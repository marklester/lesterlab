# IQ4_XS with adaptive KV streaming

This third setup has its own Compose project, container, image, and port 1236.
The existing BeeLlama and IQ3/DFlash candidates are unchanged. Its API is
`http://localhost:1236/v1` with model alias `qwen38-iq4-stream`.

The [thread's IQ4 comment](https://www.reddit.com/r/LocalLLaMA/comments/1wv6eyc/whats_the_best_setup_for_qwen38_27b_for_a_16_gig/)
reports 40–50 tokens/sec and about 200K context using Raymond's fork on a
5060-class GPU with PCIe 5.0. It does not give a complete command or exact IQ4
filename. This candidate fills those gaps using the fork's current V2 example;
it is not an exact reproduction of that comment.

## Configuration

| Setting | Value |
| --- | --- |
| Engine | Raymond's adaptive KV streaming V2, revision `e5a7b37d9ea26ce97c2882d8fef0485ccf60d971` |
| Weights | Unsloth `Qwen3.8-27B-UD-IQ4_XS.gguf`, 14.25 GB file |
| Speculation | Embedded MTP, maximum 3 draft tokens |
| Context | 204,800 total tokens, one slot |
| K / V cache | Q8_0 / Q4_0, Flash Attention enabled |
| GPU phase arena | 2,240 MiB; includes streaming KV and phase workspace |
| Batch / microbatch | 256 / 256 |
| Reasoning and sampling | Medium, preserved thinking, same thinking-mode sampling as the other candidates |
| Additional RAM prompt cache | Disabled |

The [V2 documentation](https://github.com/RaymondHuang210129/llama.cpp-adaptive-kv-streaming/blob/e5a7b37d9ea26ce97c2882d8fef0485ccf60d971/README.md)
describes a complete host KV history and shared GPU arena, including attached
MTP support. Its qualified example uses Q8_0 K, Q4_0 V, one CUDA GPU, no vision,
and 256/256 batches. I retain those choices. Its published measurements on a
5070 Ti slow substantially at long occupied context, so the Reddit speed
should be treated as a hypothesis to test.

The published 2,240 MiB arena initialized successfully on this Windows/5060 Ti
machine and served the shared-depth benchmarks. It is now the default. Total
GPU usage was about 15,914 MiB during those requests, leaving roughly 400 MiB.
The larger pool keeps more KV resident on the GPU. For more headroom, a smaller
arena such as 1,792 MiB trades GPU memory for additional host transfers; that
smaller arena has not been benchmarked here. Use actual allocation and peak
usage from [the report](BENCHMARK-COMPARISON.md), rather than weight-file size,
to assess fit.

Full KV history lives in pinned RAM even though GPU KV is bounded. Monitor
Docker/WSL RAM as well as VRAM. `--cache-ram 0` disables the additional prompt
snapshot cache, not the streaming KV history. `--load-mode none` avoids retaining
a memory mapping of the entire weight file. Unified memory is left disabled.

## Download weights in PowerShell

With the Hugging Face `hf` CLI installed:

```powershell
hf download unsloth/Qwen3.8-27B-GGUF Qwen3.8-27B-UD-IQ4_XS.gguf --revision 4ca720788d1e01f1bff70c033e0d0028fd02e502 --local-dir C:/Users/starf/.lmstudio/models/unsloth/Qwen3.8-27B-GGUF
```

The [model repository](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF) supplies
the embedded-MTP IQ4_XS file used by the fork's example. Expected SHA256:

```text
40fac4050e940397dbf13087afd50f4734a11805bf9d65ef8ddd7483470e6199
```

Set `QWEN_IQ4_MODELS_DIR` if using a different model root. Native Linux needs
an absolute Linux path for that variable.
For Windows `docker.exe` invoked from WSL, use an explicit `--env-file` with
a Windows-converted path for overrides; ordinary Linux environment assignments
are not automatically forwarded. Inspect the rendered Compose configuration
to verify the context and arena values. Native PowerShell `$env:` assignments
work directly.

## Build and switch in PowerShell

Run from the directory containing the Compose file. It builds the fork from a
pinned Git commit with pinned CUDA 12.8.1 base images, SM120 kernels for the
5060 Ti, and all Flash Attention quant combinations enabled. The build uses four
compiler jobs by default and retains objects in a BuildKit cache; compilation
can take a while. Set `QWEN_IQ4_BUILD_JOBS=2` if build RAM is limited.
The embedded browser UI is omitted; HTTP inference APIs remain available.
The build needs network access for source and Ubuntu packages. Package versions
are not locked, so this is not a bit-for-bit deterministic image build.

```powershell
docker compose -f qwen-iq4-stream.docker-compose.yaml config --quiet
docker compose -f qwen-iq4-stream.docker-compose.yaml build
```

After active requests finish, stop whichever comparison server is running:

```powershell
docker compose -f beellama.docker-compose.yaml stop
docker compose -f qwen-dflash.docker-compose.yaml stop
docker compose -f qwen-iq4-stream.docker-compose.yaml up -d --no-build --wait --wait-timeout 300
docker logs qwen38-iq4-stream-server
```

Check that logs show streaming arena initialization, the requested context,
CUDA placement, and attached MTP. Run one server on this GPU at a time.

## PCIe and comparisons

Both Windows and WSL `nvidia-smi` report maximum Gen 3 on this machine. During
inference the link runs at Gen 3 x8. This differs from the thread comment's
PCIe 5 environment. The fork keeps full KV history and recurrent rollback
checkpoints in host RAM, so host transfers matter even beyond streamed KV.
The benchmarks compare complete setups and do not isolate PCIe's contribution.

Use the existing runner from WSL, preserving the Python installation used for
your baseline:

```bash
python3 benchmark.py --label iq4-stream --base-url http://localhost:1236 --depths 8192 32768 57344 73728 --repeats 3 --output /tmp/qwen-iq4-stream
python3 benchmark.py --label iq4-stream-quality --base-url http://localhost:1236 --quality --repeats 1 --output /tmp/qwen-iq4-stream-quality
```

Then test input depths 114,688, 163,840, and 196,608 with a fresh output directory.
Thinking and final output must fit within the same window. Compare correctness,
cold prompt-processing time, generation speed, final-answer latency, and both
RAM and VRAM usage at matching depths. Disabling RAM prompt snapshots changes
repeated-request behavior, so keep cold and reused prompts separate.

To reduce the arena for more GPU memory headroom in PowerShell:

```powershell
$env:QWEN_IQ4_ARENA_MIB = "1792"
docker compose -f qwen-iq4-stream.docker-compose.yaml up -d --no-build --wait --wait-timeout 300
```

Stop the candidate and restore the existing BeeLlama container:

```powershell
docker compose -f qwen-iq4-stream.docker-compose.yaml stop
docker compose -f beellama.docker-compose.yaml start
Remove-Item Env:QWEN_IQ4_ARENA_MIB -ErrorAction SilentlyContinue
```

Windows Compose validation passed. The image was compiled locally, and the
server initialized the requested 204,800 context with embedded MTP and a
2,240 MiB arena. It completed a 196,384-token retrieval check correctly, with
12.4 minutes of cold prefill and 5.2 generation tokens/sec. The shared-depth
screen was slower than BeeLlama and passed 11/12 complete-answer checks and
10/10 short correctness cases. Measurements and hardware limits are recorded in
[BENCHMARK-COMPARISON.md](BENCHMARK-COMPARISON.md).
