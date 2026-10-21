# Qwen3.8 GSQ-RCO + DFlash2 comparison candidate

This is a separate candidate for the RTX 5060 Ti 16 GB. The existing BeeLlama
Compose file and its benchmarked setup are unchanged. The candidate has its own
Compose project (`qwen38-dflash`), container (`qwen38-dflash-server`), and port
(`1235`). Its API base URL is `http://localhost:1235/v1`.

The [Reddit thread](https://www.reddit.com/r/LocalLLaMA/comments/1wv6eyc/whats_the_best_setup_for_qwen38_27b_for_a_16_gig/)
reports 50–70 generation tokens/sec on a 5060 Ti with GSQ-RCO IQ3_S, DFlash2 Q2_K,
Q4 KV, and 512/256 batches. This is a promising comparison candidate, not a
measured improvement over your BeeLlama baseline. The report does not establish
that speed at 128K occupied context.

## Selected settings

| Setting | Candidate | Reason |
| --- | --- | --- |
| Target weights | ISTA GSQ-RCO IQ3_S, without MTP | 11.77 GB file; use a separate drafter |
| Draft weights | DFlash2 Q2_K | 705 MB file; thread's recommended drafter |
| Speculation | `draft-dflash`, maximum 4 tokens | Start with the reported 5060 Ti configuration |
| Context | 98,304 total tokens; one slot | Locally starts successfully; the 128K trial failed during CUDA allocation |
| KV cache | Q4_0 for K and V; Flash Attention on | Fit the long window in 16 GB |
| Placement | All target/draft layers on CUDA0; fit off | Explicit GPU placement; check logs for allocations |
| Batch / microbatch | 512 / 256 | Thread's suggested memory/performance balance |
| Reasoning | Medium, preserved thinking | Match the existing benchmark runner |
| Sampling | Temperature 1, top-p .95, top-k 20, min-p 0 | Qwen's thinking-mode defaults |
| RAM prompt cache | 4,096 MiB | Bound additional prompt-cache RAM |

The [ISTA model card](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF)
reports strong IQ3_S benchmark results, but weight-file size excludes KV cache,
runtime workspace, and draft state. This configuration is text-only. Its model
is the base Qwen quantization; the thread author's uncensored fine-tune is a
different set of weights.

The [draft model card](https://huggingface.co/analogalok/Qwen3.8-27B-DFlash2-Q2_K-GGUF)
contains a 4090 comparison and references the original DFlash2 PR. The pinned
upstream image uses CUDA 12.8.1, build b11347, source revision
`5fc4f3c8c7103ffd0b7ff5ee4855bcc78a3ed5cd`. DFlash2 is supported in this source;
check arguments in its [server reference](https://github.com/ggml-org/llama.cpp/blob/5fc4f3c8c7103ffd0b7ff5ee4855bcc78a3ed5cd/tools/server/README.md).
Sampling and reasoning choices follow the [Qwen model card](https://huggingface.co/Qwen/Qwen3.8-27B).

## Download the two models

Run in Windows PowerShell with the Hugging Face `hf` CLI installed. These
commands download about 12.5 GB into the existing model root, under separate
directories. Revisions are pinned, and the target filename deliberately has
no `-mtp` suffix.

```powershell
hf download ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF Qwen3.8-27B-GSQ-RCO-IQ3_S.gguf --revision d562806dbafae37109975e970aae91b43e73b440 --local-dir C:/Users/starf/.lmstudio/models/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF
hf download analogalok/Qwen3.8-27B-DFlash2-Q2_K-GGUF Qwen3.8-27B-DFlash2-Q2_K.gguf --revision d0682a20f75bf49169590cb99c1dc1c709b43b2a --local-dir C:/Users/starf/.lmstudio/models/analogalok/Qwen3.8-27B-DFlash2-Q2_K-GGUF
```

Expected SHA256 hashes (`Get-FileHash <path> -Algorithm SHA256`):

```text
64b53b64c7aa39f20a7e54bd80582fe595b1d745624ee8a72e92508c0326d810  Qwen3.8-27B-GSQ-RCO-IQ3_S.gguf
bbbcd5b66b571f438ff2018184648e37211a1d82c492d32834af2da2c7193755  Qwen3.8-27B-DFlash2-Q2_K.gguf
```

For another model root, set `QWEN_DFLASH_MODELS_DIR`. On native Linux, use an
absolute Linux path for that variable. With the default Windows bind mount,
use Windows `docker compose`, or `docker.exe` from WSL with a Windows-converted
manifest path as described in the existing README.
When setting overrides from WSL, pass a dotenv file with `--env-file` and a
Windows-converted path. Linux environment assignments do not automatically
reach Windows `docker.exe`; check `docker.exe compose ... config` to confirm
the effective context before launching. Native PowerShell `$env:` assignments
work with the commands below.

## Switch to the candidate

Run from this directory in Windows PowerShell after finishing active requests.
Both models need the same GPU: run only one server at a time. These commands
stop BeeLlama without removing its container or changing its configuration.

```powershell
docker compose -f qwen-dflash.docker-compose.yaml config --quiet
docker compose -f qwen-dflash.docker-compose.yaml pull
docker compose -f beellama.docker-compose.yaml stop
docker compose -f qwen-dflash.docker-compose.yaml up -d --wait --wait-timeout 300
docker logs qwen38-dflash-server
```

Check startup logs for the full requested context, CUDA weight/KV buffers,
and DFlash initialization. Input, thinking, and final output share the window.
The default was reduced to 98,304 after the 131,072 trial failed during a CUDA
allocation at startup. The 98,304 trial initialized DFlash and served benchmark
requests. If memory is tighter on another run, try microbatch size 128:

```powershell
$env:QWEN_DFLASH_UBATCH = "128"
docker compose -f qwen-dflash.docker-compose.yaml up -d --wait --wait-timeout 300
```

## Compare with the benchmarked baseline

Use the same Python installation, prompts, seeds, and client parameters as
the existing baseline. Compare at shared occupied depths before evaluating
the candidate's additional capacity. The runner already discovers the model
alias and sends medium reasoning and preserved thinking.

```bash
python3 benchmark.py --label gsq-dflash --base-url http://localhost:1235 --depths 8192 32768 57344 73728 --repeats 3 --output /tmp/qwen-gsq-dflash
python3 benchmark.py --label gsq-dflash-quality --base-url http://localhost:1235 --quality --repeats 1 --output /tmp/qwen-gsq-dflash-quality
```

If it passes, test 90,112 input tokens with a new output directory. A larger
context requires increasing `QWEN_DFLASH_CONTEXT` and validating startup again.
Compare completion correctness, generation speed, cold prompt-processing time,
time to final answer, and peak VRAM. Separate reused prompts from cold prompts.
Q4 KV quality at long context and DFlash acceptance depend on the workload;
measure them rather than assuming the thread's result transfers. To tune draft
length, compare `QWEN_DFLASH_DRAFT_MAX=3` against the default 4 at fixed context.
This changes engine, weights, and KV format together, so it compares whole
setups; it does not isolate which change caused a gain.

Return to the existing server from Windows PowerShell:

```powershell
docker compose -f qwen-dflash.docker-compose.yaml stop
docker compose -f beellama.docker-compose.yaml start
Remove-Item Env:QWEN_DFLASH_CONTEXT -ErrorAction SilentlyContinue
Remove-Item Env:QWEN_DFLASH_UBATCH -ErrorAction SilentlyContinue
```

The models' hashes have been verified, and the pinned image was launched
locally. The shared-depth screen passed 11/12 complete-answer checks and
10/10 short correctness cases, with roughly tied or slightly lower speed than
BeeLlama. Benchmark measurements and startup limitations are recorded in
[BENCHMARK-COMPARISON.md](BENCHMARK-COMPARISON.md).
