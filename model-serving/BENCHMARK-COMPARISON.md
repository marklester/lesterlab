# RTX 5060 Ti setup comparison — 2026-10-03

Follow-up: [matched DFlash CUDA 12 versus CUDA 13 benchmark, October 4](BENCHMARK-DFLASH-CUDA13.md).
The measurements below retain their original October 3 test conditions.

Keep the existing BeeLlama setup for generation speed within its current
window. DFlash is roughly tied or modestly slower at the shared depths, and
IQ4 streaming is substantially slower on this machine. IQ4 did successfully
retrieve the audit facts from a 196,384-token input, providing a working larger
window at a substantial latency cost.

All 67 benchmark requests are complete. The original BeeLlama configuration,
benchmark runner, and README are unchanged; BeeLlama is restored and healthy.
The two candidates remain separate, stopped containers on ports 1235 and 1236.

## Test conditions

- RTX 5060 Ti, 16,311 MiB VRAM, Windows NVIDIA driver 616.92, Docker Desktop / WSL.
- Under inference load, PCIe is Gen 3 x8. Windows also reports maximum Gen 3.
  This differs from the Reddit IQ4 comment's PCIe 5 assumption.
- WSL/Docker memory limit is about 15.3 GiB, with 4 GiB swap.
- Models were downloaded and their full SHA256 hashes verified.
- Same `benchmark.py`, Python 3.14 standard-library corpus, seeds 42/43/44,
  medium reasoning with preserved thinking, and 3,072 output-token cap.
- One GPU server at a time; no image compilation overlaps benchmark inference.
- Four shared prompt depths, three requests per depth. Actual prompts are
  8,013 / 32,589 / 57,165 / 73,549 tokens. The first request at each depth
  requests a cold prompt; the next two request cache reuse.
- Temperature 1.0, top-p 0.95, top-k 20, min-p 0, repeat penalty 1,
  presence penalty 0. Generated-token speed includes thinking.
- The long prompt retrieves three audit records from Python source, calculates
  capacity, and requests a 600–800-word review. Automated correctness checks
  only the requested JSON facts; completion checks the stop reason. These do
  not establish general coding quality or validate every review claim.
- Ten separate short correctness cases are a smoke test, one seed per case.
- This fresh baseline is used because the current corpus hash differs from
  the historical benchmark. No historical speeds are mixed into this run.

Corpus SHA256:
`805be388aa0a4ade4e51caaf1f9b430342e51c2f0a51310d7fd854e119087500`.

## Fresh BeeLlama baseline

BeeLlama v0.4.7 CUDA 13, Unsloth UD-IQ3_S with embedded MTP (draft maximum 3),
81,920 configured context, KVarN5 K / KVarN4 V with 1,024-token tail,
512/512 batches, draft microbatch 128, 4,096 MiB RAM prompt cache.

| Requested prompt depth | Median generation tok/s | Range | Cold prefill seconds | Correct JSON / complete answers |
| --- | ---: | ---: | ---: | --- |
| 8K | 43.0 | 42.7–47.3 | 11.45 | 2/3 / 1/3 |
| 32K | 34.8 | 33.6–35.9 | 48.06 | 3/3 / 3/3 |
| 56K | 30.4 | 29.0–34.4 | 93.26 | 2/3 / 2/3 |
| 72K | 27.3 | 27.1–30.7 | 127.84 | 3/3 / 3/3 |

Baseline: 10/12 correct JSON results, 9/12 complete answers, 10/10 short
correctness cases. Three long answers reached the output cap; two had no final
answer and one had correct JSON but a truncated review. Peak GPU usage during
long requests was 15,875 MiB. Peak sampled container RAM was about 2,370 MiB.

## DFlash startup adjustment

The pinned upstream CUDA 12.8 image failed at 131,072 configured context during
`cuMemSetAccess` in the startup sequence-removal probe, reporting CUDA
`device not ready`. At 98,304, it initialized and served benchmark requests.
This suggests memory pressure contributed; it does not prove the driver-level
cause. The candidate now defaults to the working 98,304 setting.
The shared-depth screen reached 73,549 input tokens; inputs near the full 96K
window were not tested.
The [startup trace](benchmarks/2026-10-03/dflash-128k-startup.log) is retained
with the compact benchmark evidence.

The separate target is ISTA GSQ-RCO IQ3_S with DFlash2 Q2_K, draft maximum 4,
Q4_0 target K/V, 512/256 batches, and 4,096 MiB RAM prompt cache. Draft K/V
remain the engine defaults. These tests compare complete setups rather than
isolating quantization, cache, or speculation changes.

| Requested prompt depth | Median generation tok/s | Range | Cold prefill seconds | Correct JSON / complete answers |
| --- | ---: | ---: | ---: | --- |
| 8K | 43.7 | 41.7–46.0 | 18.18 | 3/3 / 3/3 |
| 32K | 32.3 | 32.2–35.0 | 47.54 | 3/3 / 3/3 |
| 56K | 29.2 | 28.9–29.2 | 92.43 | 3/3 / 3/3 |
| 72K | 27.2 | 25.6–35.2 | 125.33 | 2/3 / 2/3 |

DFlash: 11/12 correct, complete answers. One 72K request spent all 3,072 output
tokens on thinking and produced no final answer. Relative to BeeLlama, median
speed changed by approximately +1.5%, −7.1%, −4.2%, and −0.6%. Three seeds do
not establish significance for small differences. The candidate offers a
larger configured window but has not demonstrated a generation-speed gain.
DFlash also passed all ten short correctness cases with complete answers.

Peak sampled VRAM was 15,461 MiB. Peak sampled container RAM was about
12,237 MiB; WSL still had at least 7,896 MiB available. The Docker RAM reading
includes reclaimable file cache, and DFlash retains the engine's default model
load mode while BeeLlama uses `--load-mode none`. Do not interpret the Docker
reading as entirely unreclaimable RAM. Additional RAM prompt caching was
enabled in both setups.

## IQ4 with adaptive KV streaming

The custom build initially failed at final linking because it lacked the
upstream CUDA Dockerfile's `-Wl,--allow-shlib-undefined` option. The Compose
build now includes it, retains build objects in a BuildKit cache, and uses
four compiler jobs. The corrected image compiled successfully and initialized
204,800 context with embedded MTP and the published 2,240 MiB arena. The
candidate now defaults to that tested arena size. The target is Unsloth
UD-IQ4_XS with draft maximum 3, Q8_0 K / Q4_0 V, 256/256 batches,
`--load-mode none`, and no additional RAM prompt cache.

| Requested prompt depth | Median generation tok/s | Range | Cold prefill seconds | Correct JSON / complete answers |
| --- | ---: | ---: | ---: | --- |
| 8K | 25.9 | 25.7–26.8 | 15.93 | 2/3 / 2/3 |
| 32K | 20.4 | 19.2–24.4 | 46.37 | 3/3 / 3/3 |
| 56K | 17.8 | 17.6–17.8 | 95.70 | 3/3 / 3/3 |
| 72K | 17.4 | 17.3–17.7 | 138.38 | 3/3 / 3/3 |

IQ4: 11/12 correct, complete answers, and 10/10 short correctness cases.
One 8K request exhausted the output budget during thinking. Generation was
roughly 36–42% slower than BeeLlama at the shared depths. Cold prefill was
close at 32K and 56K; at 72K it was about 8% slower.

Shared-depth peak VRAM was 15,914 MiB. Before the capacity probe, peak sampled
container RAM was about 8,214 MiB, with at least 5,552 MiB available to WSL.
Cache reuse was observed in subsequent requests despite `--cache-ram 0`;
that setting disables the additional RAM prompt cache, not all slot reuse.

The [fork's memory design](https://github.com/RaymondHuang210129/llama.cpp-adaptive-kv-streaming/blob/e5a7b37d9ea26ce97c2882d8fef0485ccf60d971/README.md)
stores complete KV history and recurrent rollback checkpoints in host RAM.
Gen 3 x8 host transfers
are a plausible contributor to this machine's lower throughput relative to
the thread's PCIe 5 report. Engine, weight quantization, and KV format also
changed, so these tests do not isolate the cause.

## Shared-depth comparison

| Setup | 8K tok/s | 32K tok/s | 56K tok/s | 72K tok/s | Correct, complete long answers | Short correctness cases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing BeeLlama | 43.0 | 34.8 | 30.4 | 27.3 | 9/12 | 10/10 |
| GSQ-RCO + DFlash | 43.7 | 32.3 | 29.2 | 27.2 | 11/12 | 10/10 |
| IQ4 + KV streaming | 25.9 | 20.4 | 17.8 | 17.4 | 11/12 | 10/10 |

For generation speed within the existing window, retain BeeLlama. DFlash is
essentially tied at 8K and 72K and modestly slower at the middle depths, while
offering a larger 96K configured window. IQ4's benefit is its larger context
and higher weight precision; these smoke tests do not demonstrate a coding
quality advantage. Completion counts differ under the fixed output cap, but
three seeds per depth are too few to establish broad quality differences.

## Long-context capacity check

The separate IQ4 probe targets 196,608 input tokens inside its 204,800 window.
It uses the same corpus and audit markers, but requests concise JSON rather
than the long engineering review, with seed 42 and a 1,024-token output cap.
Its throughput is not mixed into the shared-depth comparison above.
The probe passed: the returned object had all six correct integer facts,
wrapped in a Markdown JSON code fence. Actual input was 196,384 tokens, and
the answer completed with 245 generated tokens. Runtime phase telemetry
confirmed streaming was active with 768 active pages.

| Capacity-probe measurement | Result |
| --- | ---: |
| Cold prefill | 744.77 seconds / 12.4 minutes |
| Generation | 5.16 tokens/sec |
| Total request time | 792.38 seconds / 13.2 minutes |
| Time to first final-answer token | 783.34 seconds |
| Peak sampled VRAM | 15,918 MiB |

Across the full IQ4 run including this probe, peak sampled container RAM was
about 8,654 MiB, with at least 5,127 MiB available to WSL. The probe confirms
fit and retrieval for this one input; it does not establish general coding
quality or sustained long-context reliability. The thread's 40–50 tokens/sec
was not reproduced at this occupied depth on this Gen 3 x8 system.

Reproduce that separate check, with the IQ4 server running and a fresh output
directory:

```bash
python3 benchmarks/2026-10-03/capacity_probe.py --base-url http://localhost:1236 --depth 196608 --output /tmp/qwen-iq4-capacity-new
```

## Artifacts and sources

Raw request/response streams, GPU/RAM samples, rendered configurations, server
logs, and model metadata are saved locally in
`/tmp/qwen-comparison-20261003`. The existing benchmark runner is unchanged.

Compact per-request results, engine commands, image IDs, and model hashes are
saved in [comparison.json](benchmarks/2026-10-03/comparison.json).

- [Original Reddit discussion](https://www.reddit.com/r/LocalLLaMA/comments/1wv6eyc/whats_the_best_setup_for_qwen38_27b_for_a_16_gig/)
- [Pinned adaptive KV V2 documentation](https://github.com/RaymondHuang210129/llama.cpp-adaptive-kv-streaming/blob/e5a7b37d9ea26ce97c2882d8fef0485ccf60d971/README.md)
- [DFlash setup](QWEN-DFLASH.md)
- [IQ4 setup](QWEN-IQ4-STREAM.md)
