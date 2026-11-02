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