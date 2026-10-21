#!/usr/bin/env python3
"""Retain compact measurements and provenance without committing large SSE traces."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runs, summary, images, containers = {}, [], {}, {}
    for path in sorted(args.raw.glob('*/results.jsonl')):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        runs[path.parent.name] = {'metadata': json.loads((path.parent / 'metadata.json').read_text()),
                                  'requests': rows}
        for depth in dict.fromkeys(row['depth_target'] for row in rows):
            group = [row for row in rows if row['depth_target'] == depth]
            speeds = [row['timings']['predicted_per_second'] for row in group]
            cold = next((row for row in group if not row['cache_requested']), None)
            drafted = sum(row['timings'].get('draft_n', 0) for row in group)
            accepted = sum(row['timings'].get('draft_n_accepted', 0) for row in group)
            summary.append({'setup': path.parent.name, 'depth': depth, 'requests': len(group),
                            'median_tps': statistics.median(speeds),
                            'min_tps': min(speeds), 'max_tps': max(speeds),
                            'cold_prefill_seconds': cold['timings']['prompt_ms'] / 1000 if cold else None,
                            'correct': sum(row['correct'] for row in group),
                            'complete': sum(row['finish_reason'] == 'stop' for row in group),
                            'correct_and_complete': sum(row['correct'] and row['finish_reason'] == 'stop' for row in group),
                            'median_wall_seconds': statistics.median(row['wall_seconds'] for row in group),
                            'peak_vram_mib': max(row['peak_vram_mib'] for row in group),
                            'draft_acceptance': accepted / drafted if drafted else None})
    for label in ('cuda12', 'cuda13'):
        image = json.loads((args.raw / f'{label}-image.json').read_text())
        images[label] = {'id': image['Id'], 'digests': image['RepoDigests'],
                         'labels': image['Config']['Labels'],
                         'cuda_version': next(value.split('=', 1)[1] for value in image['Config']['Env']
                                              if value.startswith('CUDA_VERSION='))}
        container_path = args.raw / f'{label}-container.json'
        if container_path.exists():
            container = json.loads(container_path.read_text())[0]
            containers[label] = {'name': container['Name'], 'image': container['Image'],
                                 'command': container['Config']['Cmd'],
                                 'chat_template_kwargs': [value for value in container['Config']['Env']
                                                         if value.startswith('LLAMA_ARG_CHAT_TEMPLATE_KWARGS=')]}
    work = Path(__file__).resolve().parents[2]
    prior = json.loads((work / 'benchmarks/2026-10-03/comparison.json').read_text())
    data = {'date': '2026-10-04', 'gpu': 'NVIDIA GeForce RTX 5060 Ti', 'vram_mib': 16311,
            'windows_driver': '617.14', 'cuda_umd': '13.4', 'pcie_under_load': 'Gen 3 x8',
            'context': {label: int(container['command'][container['command'].index('--ctx-size') + 1])
                        for label, container in containers.items()}, 'python': '3.14.8',
            'benchmark_sha256': hashlib.sha256((work / 'benchmark.py').read_bytes()).hexdigest(),
            'models': [model for model in prior['models'] if 'GSQ-RCO' in model['file'] or 'DFlash2' in model['file']],
            'model_hash_note': 'SHA256 verified on 2026-10-03; reused unchanged files, not rehashed for this run',
            'raw_directory': str(args.raw), 'images': images,
            'containers': containers, 'runs': runs, 'summary': summary,
            'initial_gpu': (args.raw / 'gpu-before.txt').read_text()}
    headroom = args.raw / 'cuda13-startup-headroom.json'
    if headroom.exists():
        data['cuda13_startup_headroom'] = json.loads(headroom.read_text())
    data['excluded_diagnostics'] = {
        'aborted_cuda12': {
            'raw_directory': '/tmp/qwen-cuda-comparison-20261004',
            'idle_vram_mib': 1579, 'cancelled_after_generated_tokens': 1646,
            'sampled_windows_wsl_dedicated_mib': 15174, 'sampled_windows_wsl_shared_mib': 294,
            'reason': 'High desktop VRAM use and severe slowdown; incomplete request, excluded from comparison'},
        'cuda13_short_screen': {
            'raw_directory': '/tmp/qwen-cuda-probe96-20261004', 'idle_vram_mib': 805,
            'output_cap': 256, 'generation_tps': 57.63505079004094,
            'reason': 'Short startup screen with a different output cap; excluded from comparison'}}
    args.output.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
