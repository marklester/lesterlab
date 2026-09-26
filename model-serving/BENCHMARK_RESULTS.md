# BeeLlama benchmark — 2026-09-15

## Baseline versus proposed 80K configuration

The proposed configuration increases usable context, but did not sustain
40 generated tokens/sec on the long-context workload. Both configurations
passed the small correctness checks; these tests do not establish equivalent
accuracy for complex coding or reasoning work.

Hardware: RTX 5060 Ti, 16,311 MiB reported VRAM, driver 616.92; Ryzen 5 5600G;
32 GB host RAM, approximately 15.3 GiB available to Docker/WSL.
Model: `Qwen3.8-27B-UD-IQ3_S.gguf`. Both used the same local image ID:
`sha256:c04434ccc841408e0daff420a0a70b5a5957f6a7a81ac72be4644fafb8938154`.

| Setting | Baseline | Proposed candidate |
| --- | ---: | ---: |
| Total context capacity | 65,536 | 81,920 |
| K/V cache | kvarn5 / kvarn4 | kvarn5 / kvarn4 |
| Exact-history tail | 2,048 | 1,024 |
| Microbatch | 512 | 256 |
| RAM prompt-cache limit, MiB | 16,384 | 4,096 |
| MTP maximum draft length | 3 | 3 |
| Reasoning effort | medium | medium |

### Generation speed

Three requests per input depth, seeds 42–44. Values are median generated
tokens/sec, with the observed range in parentheses. Counts include reasoning
and visible output; prompt processing is excluded.

| Actual input tokens | Baseline 64K | Candidate 80K |
| ---: | ---: | ---: |
| 8,013 | 41.3 (36.7–42.3) | 38.1 (34.4–43.3) |
| 32,589 | 35.3 (33.5–35.8) | 33.5 (31.8–37.1) |
| 57,164 | 31.8 (30.3–34.9) | 29.1 (28.3–30.9) |
| 73,549 | Not tested: exceeds baseline capacity | 26.3 (25.9–28.8) |

At every tested input depth above 8K, all requests were below 40 t/s.
The candidate completed generations at approximately 74.8K–75.1K occupied
context; filling all 81,920 tokens was not tested.

### Prompt-processing latency

The first request at each depth disabled prompt reuse. These are single cold
prompt measurements, not medians. The server itself was not freshly restarted
for every depth.

| Actual input tokens | Baseline prompt processing | Candidate prompt processing |
| ---: | ---: | ---: |
| 8,013 | 14.9 s | 12.8 s |
| 32,589 | 48.6 s | 56.1 s |
| 57,164 | 94.9 s | 109.0 s |
| 73,549 | — | 147.7 s |

Cached repeats were much faster to begin generation. For example, at 73,549
input tokens, candidate time to first streamed token fell from 147.8 seconds
to 3.9–4.1 seconds. Full answer time still includes subsequent reasoning and
visible generation.

### Correctness and limits

- Ten short, independently checkable problems: baseline **10/10**, candidate
  **10/10**, all completed. These cover intervals, retries, scheduling, quorum,
  bin packing, probability, SQL aggregates, LRU, rollback, and token buckets.
- Long-context retrieval plus arithmetic: baseline **9/9**, candidate **12/12**
  returned the expected six JSON values.
- Complete long-form answers: baseline **8/9**, candidate **10/12**. The others
  hit the benchmark's 3,072-output-token cap after returning correct JSON but
  before completing their prose review. They are incomplete responses, not full
  successes. Neither configuration had an empty final answer in this suite.
- The long-form prompt asks for a 600–800 word review. Some traces spent many
  reasoning tokens counting words. This is a workload artifact and a useful
  example of why generation t/s and time to a complete answer can disagree.
- Peak sampled whole-GPU memory: baseline **15,536 MiB**, candidate **15,871 MiB**.
  This includes desktop/other GPU allocations and is sampled every two seconds,
  so it is not an exact model allocation or a guaranteed transient peak.
- Windows reported approximately **854 MiB shared GPU memory** after the
  candidate workload. This adapter-wide reading does not prove that model
  weights or KV cache spilled to system RAM.

## Method and reproducibility

Run `benchmark.py` as documented in README.md. It uses varied public Python
standard-library source as reference material, with three synthetic deployment
records placed across it. Requests, responses, streaming events, timing counters,
GPU samples, seeds, and the corpus hash are retained under:

`/tmp/beellama-benchmark-XUIMl6/`

Baseline results: `baseline64/results.jsonl`, `baseline64-quality/results.jsonl`.
Candidate results: `candidate80/results.jsonl` (8K),
`candidate80-long/results.jsonl` (32K/56K/72K), and
`candidate80-quality/results.jsonl`.

Every request explicitly used medium reasoning and model-card sampling:
temperature 1, top-p 0.95, top-k 20, min-p 0, presence penalty 0, repeat penalty 1.
Earlier application logs used different sampling settings and different tasks;
their speeds should not be treated as directly comparable benchmark results.

The first request per depth disabled prompt reuse; two subsequent requests
enabled it. The seed changed per repetition, so identical output text is not
expected. Even matching seeds across configurations produced different text.
Generation speed therefore measures the resulting workload, not an isolated
kernel executing an identical output sequence.

The runs were separated by a user-requested pause. An unrelated client request
was detected after the candidate's 8K group; the runner stopped before starting
32K. Remaining tests resumed on temporary port 1235 after that request finished.
The same image and model were retained, but desktop activity and memory use were
not held perfectly constant. Small speed differences should not be overinterpreted.

This is a screening suite with three long-context repetitions and one repetition
per short correctness problem. It does not establish a strict throughput floor,
application accuracy, or global optimality. It also does not substitute for a
30–60 minute representative agent/tool-use workload.
