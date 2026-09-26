# BeeLlama model serving

The Compose defaults are a tuning candidate for Qwen3.8-27B UD-IQ3_S on the
RTX 5060 Ti 16 GB: 81,920 total context tokens, medium reasoning, KVarN 5/4
KV cache, a 1,024-token precision tail, 256-token microbatches, and a 4 GiB
RAM prompt-cache limit. Context includes input, thinking, and final output.
The model directory is mounted from the Windows host through Docker Desktop.

These defaults have not been performance- or quality-qualified. The previous
65,536-token configuration produced about 37–40 generation tokens/sec at
52K–60K occupied context in existing logs. Some requests were slower. A larger
configured window does not establish either long-context accuracy or speed.

## Start or update

Run from this directory in Windows PowerShell. Updating recreates the server and interrupts active
requests; finish client work first. These commands retain the locally installed
image so a moving image tag does not change the engine during comparisons.

```powershell
docker compose -f beellama.docker-compose.yaml config --quiet
docker compose -f beellama.docker-compose.yaml up -d --pull never --wait --wait-timeout 180
```

From WSL, the Linux Compose client rejects the `C:/...` bind source. Use the
Windows client with a converted manifest path instead:

```bash
docker.exe compose -f "$(wslpath -w "$PWD/beellama.docker-compose.yaml")" up -d --pull never --wait --wait-timeout 180
```

Compose variables allow temporary experiments; their defaults remain in the
manifest. Avoid persistent shell exports or `.env` overrides during comparisons.
After choosing a winner, update the manifest defaults to record that choice.

## Find the best settings for actual work

The included standard-library-only runner saves requests, streamed responses,
server timing counters, and sampled GPU usage to a new output directory:

```bash
python3 benchmark.py --label candidate80 --depths 8192 32768 57344 73728 --repeats 3 --output /tmp/beellama-candidate80
python3 benchmark.py --label candidate80-quality --quality --repeats 1 --output /tmp/beellama-candidate80-quality
```

Run it while the server is idle. It occupies the GPU, but does not change server
configuration. The first request at each depth disables prompt reuse; subsequent
repetitions allow reuse and use seeds 43 and 44 (the first uses 42). The source
corpus is taken from installed Python standard-library files and hashed in the
results. Its actual token counts are slightly below the requested depth to leave
room for instructions. Compare runs on the same Python installation.

The long-context check combines three synthetic audit records embedded in varied
source code; the separate quality mode checks ten small reasoning problems.
`correct` means the expected JSON facts were found in the final answer. A
`finish_reason` of `length` still means the overall response was incomplete, even
when `correct` is true. The prose review is not automatically graded. These are
screening tests, not a substitute for the application tasks below.

Keep medium reasoning, sampling, model weights, GPU workload, and image constant.
Use the same saved requests and several fixed seeds for each candidate. Record
the image ID, rendered Compose configuration, model filename/hash, driver version,
request settings, responses, and server logs with each result. Client settings
can override server defaults, so check the actual request JSON.

### 1. Establish the baseline, then change one setting at a time

For a baseline run (with the corrected `preserve_thinking` spelling), save this
temporary comparison configuration as `baseline.env`:

```dotenv
BEELLAMA_CONTEXT=65536
BEELLAMA_KV_TAIL=2048
BEELLAMA_UBATCH=512
BEELLAMA_CACHE_RAM=16384
BEELLAMA_DRAFT_MAX=3
```

Apply from Windows PowerShell:

```powershell
docker compose --env-file baseline.env -f beellama.docker-compose.yaml up -d --pull never --wait --wait-timeout 180
```

This is only a comparison baseline: its 16 GiB RAM cache allowance is large
relative to the observed 15.3 GiB Docker/WSL memory limit. It is an allowance,
not a startup reservation. Monitor memory pressure during the baseline.

| Stage | Compare | Hold constant |
| --- | --- | --- |
| RAM usage | Cache RAM 16384 → 4096 MiB | Original context, tail, microbatch, and draft length |
| Workspace | Microbatch 512 → 256 | 64K context, 2048 tail, 4096 RAM cache, draft 3 |
| Recent-token precision | Tail 2048 → 1024 | 64K context, microbatch 256, RAM cache 4096, draft 3 |
| Context capacity | 65536 → 73728 → 81920 | Winning tail and microbatch; RAM cache 4096, draft 3 |
| Speculation | Draft length 2, 3, 4 | Winning context, tail, and microbatch |

Set all five variables explicitly in each comparison file so defaults do not
change an unintended setting. For the proposed defaults with draft length 2,
save `draft2.env` with:

```dotenv
BEELLAMA_CONTEXT=81920
BEELLAMA_KV_TAIL=1024
BEELLAMA_UBATCH=256
BEELLAMA_CACHE_RAM=4096
BEELLAMA_DRAFT_MAX=2
```

Then apply it:

```powershell
docker compose --env-file draft2.env -f beellama.docker-compose.yaml up -d --pull never --wait --wait-timeout 180
```

Run the plain startup command to return to the manifest defaults. Do not test
96K until 80K passes memory, speed, and quality checks.

### 2. Measure occupied context, not just configured capacity

Use fixed document/code prompts at approximately 8K, 32K, and 56K input tokens
for every candidate. For larger windows, add 64K and 72K prompts, always leaving
room for thinking and the final answer. Check actual token counts returned by
the server; characters are not tokens. Do not use repeated filler alone: it can
make speculative decoding unusually easy and does not test useful recall.

For each prompt, run at least three repetitions using the same seed list across
candidates. Separate the first request after startup from steady-state results,
and separate cold prompt processing from requests reusing a cached prefix.
Use tasks that naturally generate at least 512–1024 tokens for speed measurement;
report short-answer quality tasks separately. Keep one active request at a time.

Record these measurements per request:

- Generation tokens/sec from the server's final `eval time` line or response
  timings. Exclude `prompt eval time`; thinking tokens count as generation.
- Prompt-processing time, time to first streamed token, time to first final-answer
  token, and total time to a completed answer.
- Input/output token counts, finish reason, MTP draft acceptance, peak VRAM,
  RAM/swap usage, empty answers, errors, truncation, and repeated thinking.

Useful observation commands (run GPU monitoring in another terminal):

```bash
docker logs --since 30m beellama-server-cuda13
docker stats beellama-server-cuda13
nvidia-smi --query-gpu=timestamp,memory.used,memory.total,utilization.gpu,power.draw --format=csv -l 1
```

### 3. Score correctness before choosing the fastest result

Save 10–20 representative tasks and their expected outcomes before comparing:

- Coding changes checked by existing unit tests, including edge cases.
- Reasoning problems with independently verified answers.
- Document questions whose answers require facts near the beginning, middle,
  and end, plus a question combining facts from different positions.
- Multi-turn tool use, checking both valid arguments and successful completion.

Use the same documents and expected answers for every configuration. Test longer
documents as well as the shared shorter prompts. Simple fact retrieval alone
does not establish reasoning quality. Inspect failures rather than relying on
the model to grade itself. Run successful candidates through 30–60 minutes of
normal multi-turn use to catch cache churn, memory growth, and slowdowns.

Choose the largest window with no observed quality regression and acceptable
latency. For an approximate 40 t/s target, report median, slowest, and fraction
of requests below 40 at each context depth. If 40 is a strict floor, any measured
request below 40 fails that candidate; passing a finite sample is not a guarantee.
Treat empty answers, out-of-memory errors, and truncated reasoning as failures.
If results are close, run more repetitions; this small suite cannot prove a
globally optimal configuration. Keep the smallest memory footprint among ties.

Server timing and cache diagnostics are documented in the
[BeeLlama argument reference](https://github.com/Anbeeld/beellama.cpp/blob/main/docs/beellama-args.md)
and [server API reference](https://github.com/Anbeeld/beellama.cpp/blob/main/tools/server/README.md).
