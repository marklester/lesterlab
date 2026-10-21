#!/usr/bin/env python3
"""Run matching DFlash CUDA builds sequentially from WSL; preserve container states.

Uses the repository's unchanged benchmark.py. Raw responses stay in --output.
Requires the existing CUDA 12 container, both pinned images, and Windows Docker.
"""
import argparse
import datetime
import json
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import urllib.request

WORK = Path(__file__).resolve().parents[2]
DOCKER = '/Docker/host/bin/docker.exe'
CANDIDATES = [
    ('cuda12', 'qwen-dflash.docker-compose.yaml', 'qwen38-dflash-server', 1235),
    ('cuda13', 'qwen-dflash-cuda13.docker-compose.yaml', 'qwen38-dflash-cuda13-server', 1238),
]
SERVERS = ['beellama-server-cuda13', 'qwen38-iq4-stream-server',
           *[c[2] for c in CANDIDATES]]


def docker(*args):
    return subprocess.check_output([DOCKER, *args], cwd=WORK, text=True,
                                   stderr=subprocess.STDOUT)


def api(port, path):
    with urllib.request.urlopen(f'http://localhost:{port}{path}', timeout=10) as response:
        return json.load(response)


def winpath(path):
    return subprocess.check_output(['wslpath', '-w', str(path)], text=True).strip()


def interrupted(signum, frame):
    raise KeyboardInterrupt(f'Interrupted by signal {signum}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--depths', nargs='+', type=int, default=[8192, 32768, 57344, 73728])
    parser.add_argument('--candidates', nargs='+', choices=['cuda12', 'cuda13'], default=['cuda12', 'cuda13'])
    parser.add_argument('--max-tokens', type=int, default=3072)
    parser.add_argument('--skip-quality', action='store_true')
    parser.add_argument('--context', type=int, help='Matched override; uses a separate temporary CUDA 12 container')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    initial = {c['Name'].lstrip('/'): c for c in json.loads(docker('inspect', *SERVERS[:-1]))}
    running = sorted(set(docker('ps', '--format', '{{.Names}}').splitlines()) &
                     set([*SERVERS, 'qwen38-dflash-cuda12-bench-server']))
    if running:
        raise RuntimeError(f'Stop GPU servers before testing: {running}')
    (args.output / 'initial-containers.json').write_text(json.dumps(initial, indent=2))
    (args.output / 'gpu-before.txt').write_text(subprocess.check_output(['nvidia-smi'], text=True))
    configs = {}
    images = {}
    for label, filename, container, port in CANDIDATES:
        config = json.loads(docker('compose', '-f', winpath(WORK / filename), 'config', '--format', 'json'))
        configs[label] = config
        image = json.loads(docker('image', 'inspect', config['services']['llama']['image']))[0]
        images[label] = image
        (args.output / f'{label}-image.json').write_text(json.dumps(image, indent=2))
        (args.output / f'{label}-compose.json').write_text(json.dumps(config, indent=2))
    for key in ('command', 'environment', 'volumes', 'deploy', 'healthcheck', 'restart'):
        if configs['cuda12']['services']['llama'][key] != configs['cuda13']['services']['llama'][key]:
            raise RuntimeError(f'Inference setting mismatch: {key}')
    if initial['qwen38-dflash-server']['Config']['Cmd'] != configs['cuda12']['services']['llama']['command']:
        raise RuntimeError('Existing CUDA 12 container differs from the manifest; no changes made')
    if initial['qwen38-dflash-server']['Image'] != images['cuda12']['Id']:
        raise RuntimeError('Existing CUDA 12 container has a different image')
    revisions = {i['Config']['Labels']['org.opencontainers.image.revision'] for i in images.values()}
    if len(revisions) != 1:
        raise RuntimeError(f'Source revision mismatch: {revisions}')
    signal.signal(signal.SIGTERM, interrupted)
    for label, filename, container, port in CANDIDATES:
        if label not in args.candidates:
            continue
        manifest = WORK / filename
        temporary_control = label == 'cuda12' and args.context is not None
        if args.context is not None:
            config = json.loads(json.dumps(configs[label]))
            service = config['services']['llama']
            command = service['command']
            command[command.index('--ctx-size') + 1] = str(args.context)
            if temporary_control:
                container = 'qwen38-dflash-cuda12-bench-server'
                port = 1239
                config['name'] = 'qwen38-dflash-cuda12-bench'
                service['container_name'] = container
                service['ports'][0]['published'] = str(port)
            manifest = args.output / f'{label}-override.json'
            manifest.write_text(json.dumps(config, indent=2))
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        stop = threading.Event()
        monitor = None
        lifecycle = args.output / f'{label}-lifecycle.log'
        try:
            print(f'START SERVER {label}', flush=True)
            if label == 'cuda12' and not temporary_control:
                lifecycle.write_text(docker('start', container))
            else:
                lifecycle.write_text(docker('compose', '-f', winpath(manifest),
                                            'up', '-d', '--no-build', '--pull', 'never'))
            deadline = time.monotonic() + 300
            while True:
                try:
                    if api(port, '/health').get('status') == 'ok':
                        break
                except (OSError, ValueError):
                    pass
                if not json.loads(docker('inspect', container))[0]['State']['Running']:
                    raise RuntimeError(f'{label} server exited; see {label}-server.log')
                if time.monotonic() > deadline:
                    raise RuntimeError(f'{label} server did not become healthy within 300 seconds')
                time.sleep(2)
            (args.output / f'{label}-container.json').write_text(docker('inspect', container))

            def monitor_memory():
                with (args.output / f'{label}-memory.jsonl').open('w') as log:
                    while not stop.is_set():
                        row = {'time': time.time(), 'meminfo': Path('/proc/meminfo').read_text()}
                        try:
                            sample = subprocess.run(['/usr/bin/docker', 'stats', '--no-stream',
                                '--format', '{{json .}}', container], capture_output=True,
                                text=True, timeout=8)
                            row['docker_stats'] = sample.stdout.strip()
                            row['stats_error'] = sample.stderr.strip()
                        except subprocess.TimeoutExpired:
                            row['stats_error'] = 'timeout'
                        log.write(json.dumps(row) + '\n')
                        log.flush()
                        stop.wait(10)

            monitor = threading.Thread(target=monitor_memory, daemon=True)
            monitor.start()
            for quality in ((False,) if args.skip_quality else (False, True)):
                stage = label + ('-quality' if quality else '')
                cmd = [sys.executable, '-B', str(WORK / 'benchmark.py'), '--label', stage,
                       '--base-url', f'http://localhost:{port}', '--repeats',
                       '1' if quality else str(args.repeats), '--output', str(args.output / stage)]
                cmd += ['--max-tokens', str(args.max_tokens)]
                cmd += ['--quality'] if quality else ['--depths', *map(str, args.depths)]
                print(f'BENCHMARK {stage}', flush=True)
                with (args.output / f'{stage}-benchmark.log').open('w') as log:
                    child = subprocess.Popen(cmd, cwd=WORK, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        returncode = child.wait()
                    finally:
                        if child.poll() is None:
                            child.terminate()
                            try:
                                child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                child.kill()
                                child.wait()
                if returncode:
                    raise RuntimeError(f'{stage} benchmark failed; see {stage}-benchmark.log')
                print(f'COMPLETE {stage}', flush=True)
        finally:
            stop.set()
            if monitor:
                monitor.join(timeout=10)
            try:
                (args.output / f'{label}-server.log').write_text(docker('logs', '--since', started, container))
            finally:
                with lifecycle.open('a') as log:
                    log.write(docker('stop', container))
            print(f'STOPPED {container}', flush=True)
    print('COMPLETE; original servers remain stopped', flush=True)


if __name__ == '__main__':
    main()
