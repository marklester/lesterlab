#!/usr/bin/env python3
"""Check long-context retrieval separately from the review-writing speed screen."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('benchmark', REPO / 'benchmark.py')
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)

QUESTION = (
    'Find ALPHA, BETA, and GAMMA, combine their facts, and calculate capacity '
    'after applying the replica delta. Return only one JSON object with exactly '
    'these integer keys: start_replicas, replica_delta, requests_per_replica, '
    'final_replicas, total_capacity, remaining_capacity. Keep the reasoning concise.'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--depth', type=int, default=196608)
    parser.add_argument('--max-tokens', type=int, default=1024)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    base = args.base_url.rstrip('/')
    models = bench.api(base, '/v1/models')
    text = bench.corpus()
    tokens = bench.api(base, '/tokenize', {'content': text, 'add_special': False})['tokens']
    messages = bench.make_messages(base, tokens, args.depth)
    messages[-1]['content'] = messages[-1]['content'].removesuffix(bench.QUESTION) + QUESTION
    if any(slot.get('is_processing') for slot in bench.api(base, '/slots')):
        raise RuntimeError('Another request is active')

    payload = {
        'model': models['data'][0]['id'], 'messages': messages,
        'temperature': 1.0, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0,
        'presence_penalty': 0.0, 'repeat_penalty': 1.0,
        'chat_template_kwargs': {'reasoning_effort': 'medium', 'preserve_thinking': True},
        'seed': 42, 'max_tokens': args.max_tokens, 'cache_prompt': False,
        'stream': True, 'stream_options': {'include_usage': True}, 'timings_per_token': True,
    }
    (args.output / 'request.json').write_text(json.dumps(payload))
    metadata = {
        'corpus_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'depth_target': args.depth, 'output_cap': args.max_tokens,
        'task': 'JSON-only capacity check; not the review-writing speed screen',
    }
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    print(f'CAPACITY depth={args.depth}', flush=True)
    stop, samples = threading.Event(), []
    monitor = threading.Thread(target=bench.gpu_monitor, args=(stop, samples), daemon=True)
    monitor.start()
    try:
        result = bench.stream_request(base, payload)
    finally:
        stop.set()
        monitor.join(timeout=6)
    result['gpu_samples'] = samples
    result['correct'] = bench.grade(result['content'])
    result['depth_target'] = args.depth
    (args.output / 'response.json').write_text(json.dumps(result, indent=2))
    fields = ['correct', 'finish_reason', 'usage', 'timings', 'wall_seconds',
              'first_answer_seconds']
    print(json.dumps({key: result[key] for key in fields}), flush=True)


if __name__ == '__main__':
    main()
