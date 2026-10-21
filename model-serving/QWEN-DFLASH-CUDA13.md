# Separate DFlash CUDA 13 candidate

[qwen-dflash-cuda13.docker-compose.yaml](qwen-dflash-cuda13.docker-compose.yaml)
keeps the existing DFlash inference settings and models, with a pinned CUDA
13.4.1 image. It uses its own project `qwen38-dflash-cuda13`, container
`qwen38-dflash-cuda13-server`, and port 1238. The original BeeLlama, CUDA 12
DFlash, and IQ4 streaming manifests are unchanged.

Both DFlash images are llama.cpp b11347, source commit
`5fc4f3c8c7103ffd0b7ff5ee4855bcc78a3ed5cd`. The CUDA 13 image's Linux amd64
manifest digest is
`sha256:4c96479945dfd2387db38fc279024adbdfc1bf015aa4729ea01e5144d780d881`.
The CUDA 12 control uses CUDA 12.8.1. Avoid substituting the moving
`server-cuda13` tag when repeating this comparison: that tag can also change
the llama.cpp version.

Both candidates use GSQ-RCO IQ3_S target weights, the DFlash2 Q2_K drafter,
draft maximum 4, Q4_0 target K/V, all target/draft layers on CUDA0, 98,304
context, one slot, 512/256 batches, six CPU threads, and 4,096 MiB RAM prompt
cache. Draft K/V retain engine defaults. Reasoning is medium with thinking
preserved. Sampling is temperature 1, top-p .95, top-k 20, min-p 0, repeat
penalty 1, and presence penalty 0.

The installed driver reports CUDA UMD 13.4 and Windows KMD 617.14; this image
started on that driver. An older driver compatible only with CUDA 13.0 may
need a different CUDA 13 build.

From this directory in Windows PowerShell, after finishing active requests:

```powershell
docker compose -f qwen-dflash-cuda13.docker-compose.yaml config --quiet
docker compose -f qwen-dflash-cuda13.docker-compose.yaml pull
docker compose -f beellama.docker-compose.yaml stop
docker compose -f qwen-dflash.docker-compose.yaml stop
docker compose -f qwen-iq4-stream.docker-compose.yaml stop
docker compose -f qwen-dflash-cuda13.docker-compose.yaml up -d --wait --wait-timeout 300
docker logs qwen38-dflash-cuda13-server
```

The API base is `http://localhost:1238/v1`. Run one GPU server at a time.
Overrides use the separate prefix `QWEN_DFLASH_CUDA13_`, for example
`$env:QWEN_DFLASH_CUDA13_CONTEXT = "98304"`. With the default Windows model
path, use Windows Docker; from WSL, convert the manifest path with `wslpath -w`.
WSL environment overrides need a Windows-readable `--env-file`.

To stop this candidate and return to BeeLlama:

```powershell
docker compose -f qwen-dflash-cuda13.docker-compose.yaml stop
docker compose -f beellama.docker-compose.yaml start
```

[Benchmark results](BENCHMARK-DFLASH-CUDA13.md) cover the unchanged `benchmark.py`, the same Python
installation and corpus, seeds 42/43/44, four shared prompt depths, a 3,072
output-token cap, and ten short correctness cases per build. Raw responses
are kept outside the repository; the dated benchmark report contains the
compact results. To repeat from WSL with all GPU servers stopped and both
pinned images installed:

```bash
python3 -B benchmarks/2026-10-04/run_cuda_comparison.py \
  --output /tmp/qwen-dflash-cuda-repeat
```

The runner checks that both manifests have matching inference settings and
source revisions, starts the existing CUDA 12 container, creates/starts the
separate CUDA 13 container, and stops each after its tests. It refuses to run
when an existing GPU server is running. The existing CUDA 12 container must
already match its manifest. Use a fresh output directory for each run.
