# Mellea vs NeMo Guardrails vs plain LLM call for 5G-core config generation

All numbers below come from the runs in `hpc_results/runs/` (per-request JSONL) aggregated by `make_results.py`. Cells marked n/a were not run or are incomplete; none are estimated.

## Setup

- Hardware: DIPC Hyperion node `hyperion-282`, 1x NVIDIA A100-SXM4-80GB (driver 570.124.06, CUDA 12.8), Intel Xeon Platinum 8358, partition `preemption-gpu` (jobs 7836442 3b, 7836443 7b, 7836444 14b, 7836445 32b; stream experiment re-run 7855813; smoke job 7836373). The `general`-partition twins of each job were cancelled by the twin watcher once a preemption-gpu job started. `nvidia-smi` per job is in `hpc_results/runs/*/logs/nvidia-smi.txt`.
- Serving: vLLM 0.6.6.post1 (torch 2.5.1+cu124), OpenAI-compatible server, `--max-model-len 16384 --gpu-memory-utilization 0.85`, V0 engine, prefix caching off, guided-decoding backend `xgrammar` (default, `vllm/engine/arg_utils.py:170,372` in the cluster venv `/scratch/parefijamal/fl_llm/venv`). Models: Qwen2.5-{3B,7B,14B}-Instruct (bf16) and Qwen2.5-32B-Instruct-AWQ (4-bit, 1 GPU). Temperature 0.7, max_tokens 12000, no seed.
- Client stack (conda env on scratch, Python 3.11.18): mellea 0.8.0, nemoguardrails 0.24.1, openai 3.41.0, pydantic 2.14.2.
- Schema: Pydantic 5G-core model (PLMN, AMF with GUAMI and TAI list, SMF with DNN list and UPF N4, UPF, slices with sst 1-255 and 6-hex sd, subscribers with 15-digit IMSI and 32-hex K/OPc, mgmt with admin users). SMALL = 1-2 of each list (about 36 leaf values), LARGE = 8 slices, 10 DNNs, 40 TAIs, 30 subscribers (445 leaf values).
- Semantic checks (ground truth from the prompt): MCC/MNC, slice (sst, sd) set and count, DNN/TAI/subscriber counts, non-overlapping subnets, unique IMSIs with PLMN prefix, subscriber slice/DNN references resolve, IPs valid. Policy check: literal secrets from the prompt, weak or plaintext admin passwords (only `${ENV}` placeholders allowed), backdoor user names, auth disabled, low-entropy keys.
- Setups: Baseline = streaming chat completion, JSON requested in the prompt, parsed afterwards. Mellea = `session.instruct(..., format=Config, strategy=RejectionSamplingStrategy(loop_budget=3))` over Mellea's OpenAI backend pointed at vLLM, with 5 Python requirements built from the prompt's ground truth (structure/PLMN, slices, counts, subnets/IPs, IMSI/refs). "Mellea+policy req" (extra column) adds a sixth Python requirement implementing the policy check. NeMo-rule (C1) = Colang 1 input rail (regex/keyword: ignore-rules, backdoor, default password, DAN, hidden account, 32-hex key literal, IMSI lists) plus an output rail (Python action: Pydantic validation, then policy regex checks; invalid or violating output is blocked). NeMo-LLM-judge (C2) = built-in `self_check_input` and `self_check_output` with the same served model as judge.
- Prompt sets: SMALL 26 prompts (10 correct, 6 wrong, 5 policy, 5 benign-but-suspicious); LARGE 10 prompts (4 correct, 2 wrong, 2 policy, 2 benign) in the 3B/7B jobs, only a 6-prompt subset (3 correct, 1 wrong, 1 policy, 1 benign) in 14B/32B.
- Repetitions (n per prompt): 3B and 7B SMALL n=3, 14B SMALL n=2, 32B SMALL n=1. LARGE n=1 for 7B/14B/32B and n=2 for 3B. Mellea+policy only on correct, policy and benign prompts.
- Incomplete runs: the 3B and 7B jobs hit the 3 h limit (`TIMEOUT`, state in `hpc_results/slurm/`). Missing: 3B NeMo C1/C2 LARGE (0 rows), 3B Mellea LARGE only 8 of 20, 7B NeMo C1 LARGE 2 rows and C2 LARGE 0 rows, 3B decode-overhead test. 7B decode-overhead and streaming rows come from short extra jobs (smoke2 7836373, stream7 7855813). LARGE cells have n of 1-4 and are anecdotal, not statistics.
- Measurement notes: Baseline TTFT is the first streamed content chunk. Mellea (sampling needs the full output to validate) and NeMo (`generate_async`) are not streamed, so their TTFT equals total latency. Six baseline requests hung for ~1800 s (client timeout then SDK retry, TTFT>1500 s) and are excluded from latency stats only (they stay in validity/semantic rates); the 3B baseline also has two runaway generations (12000 tokens).
- "Blocked" outputs count as structurally invalid and semantically incorrect.
- Policy catch = delivered output contains no policy violation, or the request was blocked.

## Headline results per model (rows = metric, columns = setup)

The prescribed "recommendation per dimension" column is given once, in the section after the tables, because it holds across all four models.

Rows: 1214; client-side baseline stalls excluded from latency stats (TTFT>1500 s, request hung until the 1800 s client timeout then SDK retry): 6.

## Qwen2.5-3B-Instruct bf16 (served as `qwen2.5-3b`)

| Metric | Baseline | Mellea | NeMo-rule (C1) | NeMo-LLM-judge (C2) | Mellea+policy req (extra) |
|---|---|---|---|---|---|
| n correct-path SMALL / LARGE | 30 / 8 | 30 / 4 | 30 / 0 | 30 / 0 | 30 / 0 |
| TTFT mean s, correct SMALL (baseline = streamed; others non-streamed so TTFT = total) | 0.0 | 13.0 | 5.4 | 5.6 | 10.4 |
| Total latency mean s, correct SMALL | 4.1 | 13.0 | 5.4 | 5.6 | 10.4 |
| Total latency p50 s, correct SMALL | 4.2 | 14.9 | 5.7 | 5.8 | 10.9 |
| Total latency mean s, correct LARGE (n small, see above) | 58.0 | 275.3 | n/a | n/a | n/a |
| Failure penalty SMALL: mean(wrong) - mean(correct) | +0.1 s (wrong n=17; wasted tok/req 0) | +0.3 s (wrong n=18; wasted tok/req 1303) | +0.1 s (wrong n=18; wasted tok/req 754) | -0.1 s (wrong n=18; wasted tok/req 0) | n/a (not run) |
| Failure penalty LARGE (n=1 wrong prompt per setup unless noted) | +33 s (wrong n=4; wasted tok 0) | +56 s (wrong n=2; wasted tok 32563) | n/a (not run / incomplete) | n/a (not run / incomplete) | n/a (not run / incomplete) |
| Structural validity (Pydantic) %, correct-path SMALL (blocked = invalid) | 3% | 100% | 3% | 0% | 100% |
| Semantic correctness %, correct-path SMALL (blocked = incorrect) | 3% | 37% | 0% | 0% | 53% |
| Semantic correctness %, correct-path LARGE | 0% | 0% | n/a | n/a | n/a |
| False-positive block % (benign-but-suspicious prompts, SMALL) | 0% (n=15) | 0% (n=15) | 100% (n=15) | 0% (n=15) | 0% (n=15) |
| False-positive block % on correct-path SMALL (all benign) | 0% | 0% | 97% | 0% | 0% |
| p95 latency s (all SMALL prompts) | 6.0 | 17.3 | 6.6 | 6.7 | 16.9 |
| p99 latency s (all SMALL prompts) | 32.9 | 20.8 | 7.1 | 7.5 | 17.3 |
| Policy-violation catch % (policy prompts SMALL: blocked or clean output) | 33% (n=15) | 7% (n=15) | 100% (n=15) | 0% (n=15) | 20% (n=15) |
|   of which blocked by a rail % | 0% | 0% | 100% | 0% | 0% |
| Mean LLM calls / request (SMALL, all paths): main + judge | 1.00 + 0.00 | 2.32 + 0.00 | 0.81 + 0.00 | 1.00 + 2.00 | 2.18 + 0.00 |

## Qwen2.5-7B-Instruct bf16 (served as `qwen2.5-7b`)

| Metric | Baseline | Mellea | NeMo-rule (C1) | NeMo-LLM-judge (C2) | Mellea+policy req (extra) |
|---|---|---|---|---|---|
| n correct-path SMALL / LARGE | 30 / 4 | 30 / 4 | 30 / 2 | 30 / 0 | 30 / 0 |
| TTFT mean s, correct SMALL (baseline = streamed; others non-streamed so TTFT = total) | 0.1 | 11.9 | 7.8 | 8.0 | 11.4 |
| Total latency mean s, correct SMALL | 7.9 | 11.9 | 7.8 | 8.0 | 11.4 |
| Total latency p50 s, correct SMALL | 8.0 | 7.6 | 8.2 | 8.0 | 7.5 |
| Total latency mean s, correct LARGE (n small, see above) | 82.4 | 200.0 | 89.9 | n/a | n/a |
| Failure penalty SMALL: mean(wrong) - mean(correct) | +0.1 s (wrong n=17; wasted tok/req 0) | +5.9 s (wrong n=18; wasted tok/req 1242) | -0.0 s (wrong n=18; wasted tok/req 251) | -0.0 s (wrong n=18; wasted tok/req 129) | n/a (not run) |
| Failure penalty LARGE (n=1 wrong prompt per setup unless noted) | +8 s (wrong n=2; wasted tok 0) | +113 s (wrong n=2; wasted tok 25398) | n/a (not run / incomplete) | n/a (not run / incomplete) | n/a (not run / incomplete) |
| Structural validity (Pydantic) %, correct-path SMALL (blocked = invalid) | 90% | 100% | 77% | 50% | 100% |
| Semantic correctness %, correct-path SMALL (blocked = incorrect) | 60% | 70% | 43% | 30% | 70% |
| Semantic correctness %, correct-path LARGE | 0% | 25% | 0% | n/a | n/a |
| False-positive block % (benign-but-suspicious prompts, SMALL) | 0% (n=15) | 0% (n=15) | 33% (n=15) | 27% (n=15) | 0% (n=15) |
| False-positive block % on correct-path SMALL (all benign) | 0% | 0% | 23% | 40% | 0% |
| p95 latency s (all SMALL prompts) | 9.3 | 23.1 | 9.3 | 9.5 | 22.2 |
| p99 latency s (all SMALL prompts) | 9.4 | 23.9 | 9.5 | 10.1 | 22.6 |
| Policy-violation catch % (policy prompts SMALL: blocked or clean output) | 0% (n=15) | 0% (n=15) | 100% (n=15) | 80% (n=15) | 0% (n=15) |
|   of which blocked by a rail % | 0% | 0% | 100% | 80% | 0% |
| Mean LLM calls / request (SMALL, all paths): main + judge | 1.00 + 0.00 | 2.22 + 0.00 | 0.81 + 0.00 | 1.00 + 2.00 | 2.22 + 0.00 |

## Qwen2.5-14B-Instruct bf16 (served as `qwen2.5-14b`)

| Metric | Baseline | Mellea | NeMo-rule (C1) | NeMo-LLM-judge (C2) | Mellea+policy req (extra) |
|---|---|---|---|---|---|
| n correct-path SMALL / LARGE | 20 / 3 | 20 / 3 | 20 / 3 | 20 / 3 | 20 / 0 |
| TTFT mean s, correct SMALL (baseline = streamed; others non-streamed so TTFT = total) | 0.2 | 11.9 | 13.3 | 14.3 | 11.1 |
| Total latency mean s, correct SMALL | 14.1 | 11.9 | 13.3 | 14.3 | 11.1 |
| Total latency p50 s, correct SMALL | 14.3 | 11.5 | 13.7 | 14.4 | 11.4 |
| Total latency mean s, correct LARGE (n small, see above) | 104.9 | 120.0 | 110.5 | 98.9 | n/a |
| Failure penalty SMALL: mean(wrong) - mean(correct) | -1.6 s (wrong n=12; wasted tok/req 0) | +9.8 s (wrong n=12; wasted tok/req 721) | +0.8 s (wrong n=12; wasted tok/req 476) | -3.1 s (wrong n=12; wasted tok/req 0) | n/a (not run) |
| Failure penalty LARGE (n=1 wrong prompt per setup unless noted) | +36 s (wrong n=1; wasted tok 0) | +242 s (wrong n=1; wasted tok 16968) | -32 s (wrong n=1; wasted tok 0) | -23 s (wrong n=1; wasted tok 0) | n/a (not run / incomplete) |
| Structural validity (Pydantic) %, correct-path SMALL (blocked = invalid) | 60% | 100% | 65% | 40% | 100% |
| Semantic correctness %, correct-path SMALL (blocked = incorrect) | 60% | 100% | 65% | 40% | 100% |
| Semantic correctness %, correct-path LARGE | 33% | 100% | 0% | 33% | n/a |
| False-positive block % (benign-but-suspicious prompts, SMALL) | 0% (n=10) | 0% (n=10) | 50% (n=10) | 0% (n=10) | 0% (n=10) |
| False-positive block % on correct-path SMALL (all benign) | 0% | 0% | 35% | 5% | 0% |
| p95 latency s (all SMALL prompts) | 16.7 | 31.6 | 17.4 | 17.2 | 29.9 |
| p99 latency s (all SMALL prompts) | 17.1 | 39.4 | 18.4 | 17.6 | 37.6 |
| Policy-violation catch % (policy prompts SMALL: blocked or clean output) | 0% (n=10) | 0% (n=10) | 100% (n=10) | 80% (n=10) | 10% (n=10) |
|   of which blocked by a rail % | 0% | 0% | 100% | 80% | 0% |
| Mean LLM calls / request (SMALL, all paths): main + judge | 1.00 + 0.00 | 1.23 + 0.00 | 0.81 + 0.00 | 0.85 + 1.85 | 1.50 + 0.00 |

## Qwen2.5-32B-Instruct-AWQ (4-bit) (served as `qwen2.5-32b`)

| Metric | Baseline | Mellea | NeMo-rule (C1) | NeMo-LLM-judge (C2) | Mellea+policy req (extra) |
|---|---|---|---|---|---|
| n correct-path SMALL / LARGE | 10 / 3 | 10 / 3 | 10 / 3 | 10 / 3 | 10 / 0 |
| TTFT mean s, correct SMALL (baseline = streamed; others non-streamed so TTFT = total) | 0.4 | 17.5 | 20.7 | 21.7 | 16.0 |
| Total latency mean s, correct SMALL | 20.4 | 17.5 | 20.7 | 21.7 | 16.0 |
| Total latency p50 s, correct SMALL | 20.5 | 17.2 | 20.7 | 21.7 | 16.2 |
| Total latency mean s, correct LARGE (n small, see above) | 169.6 | 169.5 | 199.5 | 149.2 | n/a |
| Failure penalty SMALL: mean(wrong) - mean(correct) | -0.0 s (wrong n=6; wasted tok/req 0) | +13.7 s (wrong n=6; wasted tok/req 731) | -0.3 s (wrong n=6; wasted tok/req 307) | -7.2 s (wrong n=6; wasted tok/req 465) | n/a (not run) |
| Failure penalty LARGE (n=1 wrong prompt per setup unless noted) | +27 s (wrong n=1; wasted tok 0) | +334 s (wrong n=1; wasted tok 16733) | -2 s (wrong n=1; wasted tok 0) | +62 s (wrong n=1; wasted tok 7034) | n/a (not run / incomplete) |
| Structural validity (Pydantic) %, correct-path SMALL (blocked = invalid) | 100% | 100% | 100% | 0% | 100% |
| Semantic correctness %, correct-path SMALL (blocked = incorrect) | 100% | 100% | 100% | 0% | 100% |
| Semantic correctness %, correct-path LARGE | 67% | 100% | 100% | 0% | n/a |
| False-positive block % (benign-but-suspicious prompts, SMALL) | 0% (n=5) | 0% (n=5) | 80% (n=5) | 60% (n=5) | 0% (n=5) |
| False-positive block % on correct-path SMALL (all benign) | 0% | 0% | 0% | 100% | 0% |
| p95 latency s (all SMALL prompts) | 23.7 | 43.1 | 23.8 | 25.0 | 43.2 |
| p99 latency s (all SMALL prompts) | 24.3 | 53.7 | 24.3 | 25.4 | 51.4 |
| Policy-violation catch % (policy prompts SMALL: blocked or clean output) | 0% (n=5) | 0% (n=5) | 100% (n=5) | 100% (n=5) | 20% (n=5) |
|   of which blocked by a rail % | 0% | 0% | 100% | 100% | 0% |
| Mean LLM calls / request (SMALL, all paths): main + judge | 1.00 + 0.00 | 1.23 + 0.00 | 0.81 + 0.00 | 0.73 + 1.73 | 1.40 + 0.00 |

## Constrained decoding (vLLM guided_json / xgrammar) per-token overhead, same prompt c0, with vs without `response_format` json_schema

| model | size | mode | n | mean TTFT s | mean decode ms/token (client side, (latency-TTFT)/(tokens-1)) | mean completion tokens |
|---|---|---|---|---|---|---|
| qwen2.5-14b | small | free | 3 | 0.11 | 20.31 | 543 |
| qwen2.5-14b | small | schema | 3 | 0.80 | 20.77 | 404 |
| qwen2.5-14b | large | free | 1 | 0.12 | 20.61 | 5066 |
| qwen2.5-14b | large | schema | 1 | 0.80 | 21.13 | 4744 |
| qwen2.5-32b | small | free | 2 | 0.43 | 28.93 | 583 |
| qwen2.5-32b | small | schema | 2 | 1.15 | 29.40 | 403 |
| qwen2.5-32b | large | free | 1 | 0.43 | 29.46 | 6648 |
| qwen2.5-32b | large | schema | 1 | 1.14 | 29.85 | 5569 |
| qwen2.5-7b | small | free | 1 | 0.06 | 11.08 | 580 |
| qwen2.5-7b | small | schema | 1 | 13.97 | 11.91 | 403 |
| qwen2.5-7b | large | free | 1 | 0.06 | 11.32 | 7225 |
| qwen2.5-7b | large | schema | 1 | 0.71 | 12.05 | 7392 |
| qwen2.5-3b | - | - | 0 | n/a | n/a (3B job hit the 3 h limit before this step) | n/a |
### NeMo streaming with output rails (7B, vLLM, model served as qwen2.5-7b; `stream_exp.py`, 4 prompts x 2 reps, 40 rows)

| Variant | TTFT s (mean) | What the client receives |
|---|---|---|
| S0 `stream_async`, no rails | 0.08-0.49 | token-by-token stream (545-695 chunks) |
| S1 output rail, `stream_first: true`, chunk_size 200 | 2.29 | first data after a 200-token buffer, then 201 chunks (about 600-760 chars) of the config stream out, then the block JSON error appended |
| S2 output rail, `stream_first: false` | 2.29 (time to the single block message) | one chunk: `{"error": {"message": "Blocked by check output config rails.", ... "type": "guardrails_violation", "code": "content_blocked"}}`; nothing of the config is shown |
| S3 output rail configured, `streaming.enabled: false` | n/a | `StreamingNotSupportedError` (message in the rows) |
| G1 `generate_async` with output rail | = total latency (6.1-7.7) | full text if allowed, else the canned `I'm sorry, I can't respond to that.` (35 chars) |

In S1/S2 every prompt was blocked, including prompts whose full output passes in G1. The reason (inferred from the setup, not separately tested) is that the rail runs on a partial 200-token window and the C1 action validates a complete JSON document, so a truncated chunk fails schema validation. A streaming rail for structured output has to be chunk-aware. 200 tokens at ~11 ms/token on the 7B model is the 2.29 s TTFT, so the "TTFT cost" of chunked output rails equals chunk_size x per-token time. The G1 results across the two reps differ for c0/c2 (one rep blocked, one passed) because outputs are sampled at temperature 0.7 and the validity of the baseline output varies.

## Answers to the five questions

1. Where does Mellea's constrained decoding happen, and what does RejectionSamplingStrategy do with failed samples? Constrained decoding happens inside the serving backend during generation: Mellea only forwards the Pydantic JSON schema (`mellea/backends/openai.py:1421-1427` sends `response_format={"type":"json_schema","json_schema":{"name":..,"schema":Model.model_json_schema(),"strict":True}}` for non-OpenAI servers; the OpenAI-platform variant at `openai.py:1410-1418` adds `additionalProperties=False`; the Ollama backend does the same with `format=` at `mellea/backends/ollama.py:1178`). The grammar enforcement itself is vLLM's xgrammar logit masking (not in Mellea's source). `RejectionSamplingStrategy` is the discard-and-resample variant: after generation (`mellea/stdlib/sampling/base.py:508-515`) and validation, on failure the loop calls `repair` (`base.py:604-608`), which for this strategy returns the unedited last action and the old context (`base.py:659-678`), so the next attempt is a blind re-roll with no feedback. If the budget is exhausted, `select_from_failure` returns index 0 (`base.py:641-656`), i.e. the first failed sample is returned with `success=False`. The final iteration skips repair (`base.py:597-600` region). Failed samples are therefore discarded, not repaired; `RepairTemplateStrategy` (`base.py:681-745`) is the feedback variant and was not benchmarked.
2. Do NeMo default output rails run after full generation? Yes in `generate_async`: the flow `run output rails` runs on the finished bot message (`nemoguardrails/rails/llm/llm_flows.co:173-202`). Streaming output rails are opt-in: `rails.output.streaming` defaults to `enabled=False, chunk_size=200, context_size=50, stream_first=True` (`rails/llm/config.py:374-390`), and `stream_async` raises `StreamingNotSupportedError` if output rails exist without `streaming.enabled` (`rails/llm/llmrails.py:1368-1375`, confirmed empirically in S3 above). With streaming, rails run per chunk (`llmrails.py:1930-1951`; `stream_first=False` yields chunks after the rails, `llmrails.py:2104`).
3. What is returned on block? In `generate_async`, the canned text `I'm sorry, I can't respond to that.` (defined for each built-in flow, e.g. `library/self_check/output_check/flows.v1.co:1-2`; observed verbatim in all blocked rows and in G1). In streaming mode a JSON error string with `type: guardrails_violation, code: content_blocked` is yielded instead (S1/S2 above). No regeneration happens in either mode; the blocked generation is wasted (see wasted-token rows).
4. TTFT with output rails on vs off: see the streaming table: 0.08-0.49 s without rails vs 2.29 s with rails and chunk_size 200 (both `stream_first` values in this run: with `stream_first: true` the first 200 tokens are buffered before any chunk reaches the client in these runs; the block is announced only after the chunk is delivered, so content can leak). Without streaming (what the main benchmark used) TTFT equals total latency.
5. Constrained-decoding decode overhead: see the decode-overhead table. With vLLM xgrammar the per-token decode time rises by about 0.5 ms/token (14B 20.31 to 20.77, +2.3%; 32B-AWQ 28.93 to 29.40, +1.6%; 7B 11.08 to 11.91, +7.5% but n=1) at both SMALL and LARGE; there is a constant TTFT cost of about 0.7 s (grammar compile for the large schema, cached afterwards) and a 14 s cold first-request compile once on the 7B smoke job. The overhead does not grow with output size in these runs (14B LARGE +0.52 ms/token, 32B LARGE +0.39 ms/token). Constrained output is more compact (no pretty-print whitespace: ~400 vs ~580 tokens at SMALL), so end-to-end latency is often lower despite the per-token cost.

## Recommendation per dimension

| Dimension | Recommendation | Evidence |
|---|---|---|
| TTFT / streaming UX | Baseline (or NeMo with no output rails). Mellea sampling and non-streamed NeMo give TTFT = full latency; chunked NeMo output rails add chunk_size x token time (2.3 s on 7B). | TTFT row, streaming table |
| Latency, correct path | Mellea is not slower than baseline at 14B (11.9 vs 14.1 s) because constrained output is shorter, but is slower on a small model that fails its requirements (3B: 13.0 vs 4.1 s, 2.37 calls). NeMo-rule adds no measurable latency over baseline; C2 adds 2 short judge calls (cheap, 2-4 tokens). | latency rows, calls row |
| Failure penalty / tail | NeMo (fail-closed, no retry) has the smallest tail but wastes the blocked generation; Mellea tail grows with retries (LARGE: +242 s at 14B and +334 s at 32B for one wrong prompt, 3 x 5-7k tokens wasted). Use a small loop_budget or fail fast on LARGE outputs. | failure penalty, p95/p99 rows |
| Structural validity | Mellea (100% on every model, enforced by the grammar). NeMo and baseline depend on the model; below 14B baseline is poor (3B 3%, 7B 90%, 14B 60%). | validity rows |
| Semantic correctness | Mellea with prompt-derived requirements (14B 100% vs baseline 60%); the benefit shrinks when the model cannot satisfy requirements in 3 tries (3B 37%). NeMo cannot add correctness: it only blocks. | semantic rows |
| Policy / jailbreak coverage | NeMo-rule input and output rails (100% catch on these prompts, which were written knowing the regex vocabulary, so treat it as an upper bound). NeMo-LLM-judge catches 80-100% on 7B+ but 0% on the 3B judge. Mellea alone catches 0% (7B+); adding a policy requirement does not fix a request that asks for the violation (10-20% at 14B/32B), so policy belongs in a rail, not in the retry loop. | policy rows |
| False positives | NeMo-rule input rail produced 0 input-rail false positives on the benign-but-suspicious prompts; its measured FP block rates on the benign-but-suspicious prompts (33% at 7B, 50% at 14B, 100% at 3B) are output-rail blocks of schema-invalid JSON, consistent with each model's baseline invalid rate, not policy FPs (a per-row policy/structure split is not recorded). The LLM judge blocks valid benign outputs (32B-AWQ: 10/10 correct-path outputs blocked; 7B: 12/30). | FP rows, per-row `blocked_by` |
| Best combination (suggested, not benchmarked) | Mellea for structure and semantics plus NeMo-rule rails for policy, with the model judge reserved for fuzzy policy only. | derived from the above |

## Not directly comparable

- Baseline and Mellea receive the same task prompt, but Mellea adds its own instruction template and the five requirement texts to the prompt, and NeMo wraps the prompt in its general-chat template. Prompt tokens differ across setups.
- Only Mellea's validators were given the per-prompt ground truth (counts, PLMN, slice set). NeMo's output rail validates schema and policy only, so its semantic correctness cannot exceed what the model produced; this is intrinsic to rails but means the semantic-correctness column favours Mellea by construction.
- The Baseline/NeMo requests are unconstrained, Mellea's are grammar-constrained, so output lengths differ (Mellea ~500 vs ~680 tokens on 14B).
- TTFT: only the baseline streams in the main matrix; Mellea and NeMo TTFT equal total latency by design of the measured API call.
- LARGE results have n of 1-4 per cell (the 3B/7B jobs timed out, 14B/32B ran only a 6-prompt subset); SMALL n differs per model (3, 3, 2, 1). Treat LARGE and 32B numbers as indicative.
- The 14B vs 32B-AWQ comparison mixes precision (bf16 vs 4-bit) with size. Latency across models is not a pure model-size effect.
- The NeMo C2 judge is the same served model as the generator (3B judging 3B), which is a weak judge by design; a separate stronger judge was not tested. C2 judge verdicts depend on my two prompt texts in `nemo_c2/prompts.yml`.
- Policy prompts and the C1 regexes were written by the same author, so C1's 100% policy catch is optimistic. Output-side policy violations are scored by my own detector (`common.policy_violations`).
- The local Jetson Thor rows from earlier in the session used Ollama (GGUF Q4, 3B only, partial) and a different harness; they are kept in `results/` and `ollama_local/` and are not comparable with these vLLM numbers.
- Sampling is not seeded (temperature 0.7), so repeated runs differ.
- The 3B/7B jobs started and ended at different times on different SXM4 cards of the same node type; vLLM was cold-started per job.
- `nemo_c1/actions.py` was edited after the 3B/7B/14B/32B runs only to replace a hard-coded `sys.path` entry by an environment-variable default; the rail logic is unchanged.
