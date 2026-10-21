# DFlash CUDA 12 versus CUDA 13 — 2026-10-04

Keep the existing CUDA 12 DFlash profile for this workload and output budget.
CUDA 13 generated tokens faster at 8K and 32K, but was slower at 56K and 72K,
had slower cold prefill at every depth, and completed fewer long answers.
These are results for the two official builds on this machine, not a general
claim about CUDA 13 or model accuracy.

All 44 comparison requests are complete: 12 long requests and 10 short
correctness checks per build. Both builds started and served at the existing
98,304 configured context. Maximum tested input was 73,549 tokens; inputs
near the full 96K window were not tested.

The original BeeLlama, CUDA 12 DFlash, and IQ4 manifests are unchanged.
They were stopped before testing and remain stopped. The separate CUDA 13
candidate is also stopped.

## Matched builds and settings

| Setting | CUDA 12 control | CUDA 13 candidate |
| --- | --- | --- |
| CUDA toolkit/runtime | 12.8.1 | 13.4.1 |
| llama.cpp version | b11347 | b11347 |
| Source commit | `5fc4f3c8c7103ffd0b7ff5ee4855bcc78a3ed5cd` | Same |
| Reported host compiler | GNU 14.2.0, Linux x86_64 | Same |
| Image manifest SHA256 | `d87b02aafa74797a2d599b281c50468704bd0bcdc57bfcf31b570d593f1d285b` | `4c96479945dfd2387db38fc279024adbdfc1bf015aa4729ea01e5144d780d881` |
| Container | `qwen38-dflash-server` | `qwen38-dflash-cuda13-server` |
| Host port | 1235 | 1238 |

Image labels, the binaries' `--version` output, and API build information
confirmed matching source revisions. The comparison changes the official
CUDA build, including its compiler/toolkit and libraries; it is not a test
of swapping one runtime library in an otherwise identical binary.

Both use the same existing GSQ-RCO IQ3_S target and DFlash2 Q2_K drafter.
Settings match: all target/draft layers on CUDA0, `draft-dflash` maximum 4,
Q4_0 target K/V, draft K/V defaults, Flash Attention on, fit off, one slot,
512/256 batches, six threads, 4,096 MiB RAM prompt cache, and medium reasoning
with thinking preserved. Sampling is temperature 1, top-p .95, top-k 20,
min-p 0, repeat penalty 1, and presence penalty 0.

The existing model hashes were verified on October 3 and were not rehashed
for this run. Both containers mounted the same model directory read-only.
Hashes and filenames are retained in the compact evidence.

## Generation and completion

Median generation speed includes both thinking and final-answer tokens.
Each depth has three seeds, 42/43/44, and a 3,072-token output cap. A complete
answer requires `finish_reason=stop`; correctness checks the final answer's
requested JSON facts, not the entire engineering review.

| Prompt depth | CUDA 12 tok/s | CUDA 13 tok/s | Change | Correct, complete: CUDA 12 | Correct, complete: CUDA 13 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8K | 43.7 | 46.6 | +6.6% | 3/3 | 0/3 |
| 32K | 32.3 | 36.8 | +13.8% | 3/3 | 1/3 |
| 56K | 29.2 | 25.3 | −13.4% | 3/3 | 3/3 |
| 72K | 27.2 | 23.1 | −14.9% | 2/3 | 2/3 |

Generation ranges were 40.2–46.0 / 32.3–35.0 / 28.9–29.2 / 25.6–35.2 tok/s
for CUDA 12, and 45.5–47.8 / 30.4–37.2 / 25.0–25.8 / 22.9–26.7 for CUDA 13.

| Check | CUDA 12 | CUDA 13 |
| --- | ---: | ---: |
| Long answers with correct final JSON | 11/12 | 7/12 |
| Long answers with correct JSON and completed output | 11/12 | 6/12 |
| Short correctness checks, correct and complete | 10/10 | 10/10 |

CUDA 12 had one request exhaust the budget during thinking. CUDA 13 had
five such requests, plus one that returned correct JSON but a truncated
review. Its three 8K requests all spent the budget on thinking, including
drafting the review inside reasoning, and emitted no final answer.

The requests used identical seeds, but sampled outputs, thinking lengths,
and draft acceptance differed between builds. Higher token throughput is
therefore not necessarily faster delivery of the same answer. These small
smoke tests do not establish a general quality regression or statistical
significance. A larger reasoning/output budget was not tested.

## Cold prompt processing

Actual inputs were 8,013 / 32,589 / 57,165 / 73,549 tokens. The first request
at each depth requested no prompt-cache reuse; subsequent requests requested
reuse. Both builds reported zero cached tokens for the cold request and
reuse for the next two. The figures below are engine prompt-processing time,
separate from startup and generation.

| Prompt depth | CUDA 12 seconds | CUDA 13 seconds | Change |
| --- | ---: | ---: | ---: |
| 8K | 11.45 | 12.24 | +6.9% |
| 32K | 47.55 | 55.67 | +17.1% |
| 56K | 91.47 | 114.81 | +25.5% |
| 72K | 126.35 | 162.83 | +28.9% |

## Test conditions and excluded diagnostics

- RTX 5060 Ti, 16,311 MiB VRAM; Windows driver 617.14, CUDA UMD 13.4.
- Docker Desktop / WSL; about 15.3 GiB VM RAM and 4 GiB swap.
- PCIe Gen 3 x8 under load.
- Fresh CUDA 12 control on the same driver as CUDA 13; October 3 speeds are
  not mixed into these tables.
- One GPU server at a time; no compilation or image downloads during inference.
- Unchanged `benchmark.py`, Python 3.14.8, same corpus SHA256
  `805be388aa0a4ade4e51caaf1f9b430342e51c2f0a51310d7fd854e119087500`.
- Long task: retrieve three audit records from source-code filler, calculate
  capacity, and write a 600–800-word review. No generated code was executed.
- Runs were sequential, CUDA 12 then CUDA 13. Desktop GPU memory is not
  perfectly controlled. The control began with 708 MiB used; CUDA 13 startup,
  before its weights loaded, was sampled at 839 MiB.
- Peak sampled GPU usage across all requests was 15,961 MiB for CUDA 12 and
  15,968 MiB for CUDA 13. This does not demonstrate a memory-capacity gain.

An initial CUDA 12 request began with 1,579 MiB of idle GPU use and slowed to
about 8 tok/s. Windows counters sampled the WSL process at 15,174 MiB dedicated
and 294 MiB shared GPU memory. The near-full VRAM and shared usage are consistent
with memory pressure, but do not prove which allocations were paged.
The request was deliberately canceled after 1,646 generated tokens; its
[diagnostic log](benchmarks/2026-10-04/initial-memory-pressure.log) is retained.

A subsequent CUDA 13 startup screen, with 805 MiB idle GPU use and a 256-token
output cap, generated at 57.6 tok/s. Its different memory headroom and short
output budget prevent a useful comparison with the canceled control. Both
diagnostics are excluded from the 44-request tables. Both builds were
restarted for the full comparison after idle GPU use fell near 700 MiB.

The 96K configuration is tight on this desktop: the observed high idle GPU
footprint can materially hurt performance. An 80K context fallback was
prepared in the runner but was not benchmarked.

## Artifacts and use

- [Separate CUDA 13 Compose file](qwen-dflash-cuda13.docker-compose.yaml).
- [PowerShell commands and pinned-image details](QWEN-DFLASH-CUDA13.md).
- [Compact results, per-request timings, and provenance](benchmarks/2026-10-04/comparison.json).
- [Sequential benchmark runner](benchmarks/2026-10-04/run_cuda_comparison.py).
- [Result summarizer](benchmarks/2026-10-04/summarize_cuda_comparison.py).

Full requests, SSE responses, GPU samples, memory samples, image/container
inspections, rendered Compose configurations, and lifecycle logs are in
`/tmp/qwen-cuda-matched96-20261004`. Excluded diagnostics are in
`/tmp/qwen-cuda-comparison-20261004` and `/tmp/qwen-cuda-probe96-20261004`.
Strata was skipped; no Strata model was downloaded or benchmarked.
