"""Aggregate HPC results -> tables.md, summary CSVs. Rows with a client-side TTFT stall (>1500 s) are excluded from latency stats only."""
import csv, glob, json, os
import numpy as np
rows = []
for f in sorted(glob.glob("hpc_results/runs/[0-9]*/results/*_small_*.jsonl") + glob.glob("hpc_results/runs/[0-9]*/results/*_large_*.jsonl")):
    for l in open(f):
        d = json.loads(l); d["stall"] = bool(d.get("ttft") and d["ttft"] > 1500 and d["setup"] == "baseline"); rows.append(d)
MODELS = [("qwen2.5-3b", "Qwen2.5-3B-Instruct bf16"), ("qwen2.5-7b", "Qwen2.5-7B-Instruct bf16"), ("qwen2.5-14b", "Qwen2.5-14B-Instruct bf16"), ("qwen2.5-32b", "Qwen2.5-32B-Instruct-AWQ (4-bit)")]
S = ["baseline", "mellea", "nemo_c1", "nemo_c2"]; SN = {"baseline": "Baseline", "mellea": "Mellea", "nemo_c1": "NeMo-rule (C1)", "nemo_c2": "NeMo-LLM-judge (C2)", "mellea_pol": "Mellea+policy req"}
def pick(model, size=None, setup=None, path=None):
    return [r for r in rows if r["model"] == model and (size is None or r["size"] == size) and (setup is None or r["setup"] == setup) and (path is None or r["path"] == path) and "error" not in r]
def lat(x): return [r["latency"] for r in x if not r["stall"]]
def mean(x): return f"{np.mean(x):.1f}" if x else "n/a"
def pc(x, q): return f"{np.percentile(x, q):.1f}" if x else "n/a"
def rate(x): return f"{100 * sum(x) / len(x):.0f}%" if x else "n/a"
out = []; csvrows = []
def P(s=""): out.append(s)
nstall = sum(r["stall"] for r in rows)
P(f"Rows: {len(rows)}; client-side baseline stalls excluded from latency stats (TTFT>1500 s, request hung until the 1800 s client timeout then SDK retry): {nstall}.\n")
for model, label in MODELS:
    if not pick(model): continue
    P(f"## {label} (served as `{model}`)\n")
    P("| Metric | Baseline | Mellea | NeMo-rule (C1) | NeMo-LLM-judge (C2) | Mellea+policy req (extra) |")
    P("|---|---|---|---|---|---|")
    def row(name, fn, cols=S + ["mellea_pol"]):
        cells = []
        for s in cols:
            try: v = fn(s)
            except Exception as e: v = "n/a"
            cells.append(v)
        P(f"| {name} | " + " | ".join(cells) + " |")
        csvrows.append([model, name] + cells)
    def n_(s, size, path): return len(pick(model, size, s, path))
    row("n correct-path SMALL / LARGE", lambda s: f"{n_(s,'small','correct')} / {n_(s,'large','correct')}")
    row("TTFT mean s, correct SMALL (baseline = streamed; others non-streamed so TTFT = total)", lambda s: mean([r['ttft'] for r in pick(model, 'small', s, 'correct') if r['ttft'] and not r['stall']]))
    row("Total latency mean s, correct SMALL", lambda s: mean(lat(pick(model, 'small', s, 'correct'))))
    row("Total latency p50 s, correct SMALL", lambda s: pc(lat(pick(model, 'small', s, 'correct')), 50))
    row("Total latency mean s, correct LARGE (n small, see above)", lambda s: mean(lat(pick(model, 'large', s, 'correct'))))
    def pen(s):
        c = lat(pick(model, 'small', s, 'correct')); w = lat(pick(model, 'small', s, 'wrong'))
        if not w or not c: return 'n/a (not run)'
        return f"{np.mean(w) - np.mean(c):+.1f} s (wrong n={len(w)}; wasted tok/req {np.mean([r['wasted_tokens'] for r in pick(model,'small',s,'wrong')]):.0f})"
    row("Failure penalty SMALL: mean(wrong) - mean(correct)", pen)
    def penl(s):
        c = lat(pick(model, 'large', s, 'correct')); w = lat(pick(model, 'large', s, 'wrong'))
        if not w or not c: return 'n/a (not run / incomplete)'
        return f"{np.mean(w) - np.mean(c):+.0f} s (wrong n={len(w)}; wasted tok {np.mean([r['wasted_tokens'] for r in pick(model,'large',s,'wrong')]):.0f})"
    row("Failure penalty LARGE (n=1 wrong prompt per setup unless noted)", penl)
    row("Structural validity (Pydantic) %, correct-path SMALL (blocked = invalid)", lambda s: rate([r['struct_valid'] for r in pick(model, 'small', s, 'correct')]))
    row("Semantic correctness %, correct-path SMALL (blocked = incorrect)", lambda s: rate([r['sem_correct'] for r in pick(model, 'small', s, 'correct')]))
    row("Semantic correctness %, correct-path LARGE", lambda s: rate([r['sem_correct'] for r in pick(model, 'large', s, 'correct')]))
    row("False-positive block % (benign-but-suspicious prompts, SMALL)", lambda s: rate([r['blocked'] for r in pick(model, 'small', s, 'benign_susp')]) + f" (n={n_(s,'small','benign_susp')})")
    row("False-positive block % on correct-path SMALL (all benign)", lambda s: rate([r['blocked'] for r in pick(model, 'small', s, 'correct')]))
    row("p95 latency s (all SMALL prompts)", lambda s: pc(lat(pick(model, 'small', s)), 95))
    row("p99 latency s (all SMALL prompts)", lambda s: pc(lat(pick(model, 'small', s)), 99))
    row("Policy-violation catch % (policy prompts SMALL: blocked or clean output)", lambda s: rate([(r['blocked'] or not r['policy_viol']) for r in pick(model, 'small', s, 'policy')]) + f" (n={n_(s,'small','policy')})")
    row("  of which blocked by a rail %", lambda s: rate([r['blocked'] for r in pick(model, 'small', s, 'policy')]))
    row("Mean LLM calls / request (SMALL, all paths): main + judge", lambda s: f"{np.mean([r['main_calls'] for r in pick(model,'small',s)]):.2f} + {np.mean([r['judge_calls'] for r in pick(model,'small',s)]):.2f}")
    P("")
# decode overhead + stream
P("## Constrained decoding (vLLM guided_json / xgrammar) per-token overhead, same prompt c0, with vs without `response_format` json_schema\n")
P("| model | size | mode | n | mean TTFT s | mean decode ms/token (client side, (latency-TTFT)/(tokens-1)) | mean completion tokens |")
P("|---|---|---|---|---|---|---|")
src = {"qwen2.5-14b": "14b", "qwen2.5-32b": "32b", "qwen2.5-7b": "smoke2"}
for model, d in src.items():
    f = glob.glob(f"hpc_results/runs/{d}/results/decode_overhead_*.json")
    if not f: continue
    R = json.load(open(f[0]))
    for size in ("small", "large"):
        for mode in ("free", "schema"):
            x = [r for r in R if r["size"] == size and r["mode"] == mode]
            if x: P(f"| {model} | {size} | {mode} | {len(x)} | {np.mean([r['ttft'] for r in x]):.2f} | {np.mean([r['decode_ms_per_tok'] for r in x]):.2f} | {np.mean([r['completion_tokens'] for r in x]):.0f} |")
P("| qwen2.5-3b | - | - | 0 | n/a | n/a (3B job hit the 3 h limit before this step) | n/a |")
open("tables.md", "w").write("\n".join(out)); 
with open("summary_headline.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["model", "metric"] + [SN[s] for s in S + ["mellea_pol"]]); w.writerows(csvrows)
print("\n".join(out))
