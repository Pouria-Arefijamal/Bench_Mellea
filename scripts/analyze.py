import glob, json, os, statistics as st
import numpy as np
rows = []
for f in sorted(glob.glob("hpc_results/runs/[0-9]*/results/*_small_*.jsonl") + glob.glob("hpc_results/runs/[0-9]*/results/*_large_*.jsonl")):
    for l in open(f):
        d = json.loads(l)
        if "error" in d: d["_err"] = True
        rows.append(d)
SETUPS = ["baseline", "mellea", "mellea_pol", "nemo_c1", "nemo_c2"]
def sel(**kw): return [r for r in rows if all(r.get(k) == v for k, v in kw.items()) and "error" not in r]
def pct(x, q): return float(np.percentile(x, q)) if x else float("nan")
def m(x): return float(np.mean(x)) if x else float("nan")
def rate(x): return 100 * sum(x) / len(x) if x else float("nan")
out = []
def P(s=""): out.append(s)
errs = [r for r in rows if "error" in r]
P(f"error rows (excluded): {len(errs)}")
for model in sorted({r["model"] for r in rows}):
    for size in ("small", "large"):
        R = sel(model=model, size=size)
        if not R: continue
        P(f"\n### {model} / {size}\n")
        P("| setup | path | n | mean s | p50 s | p95 s | p99 s | struct-valid % | sem-correct % | blocked % | blocked by in/out | mean main calls | mean judge calls | wasted tok (mean) | gen tok (mean) | judge tok (mean) | policy viol delivered % |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for s in SETUPS:
            for path in ("correct", "wrong", "policy", "benign_susp", "ALL"):
                x = [r for r in R if r["setup"] == s and (path == "ALL" or r["path"] == path)]
                if not x: continue
                lat = [r["latency"] for r in x]
                bi = sum(1 for r in x if r.get("blocked_by") == "input"); bo = sum(1 for r in x if r.get("blocked_by") == "output")
                P(f"| {s} | {path} | {len(x)} | {m(lat):.1f} | {pct(lat,50):.1f} | {pct(lat,95):.1f} | {pct(lat,99):.1f} | {rate([r['struct_valid'] for r in x]):.0f} | {rate([r['sem_correct'] for r in x]):.0f} | {rate([r['blocked'] for r in x]):.0f} | {bi}/{bo} | {m([r['main_calls'] for r in x]):.2f} | {m([r['judge_calls'] for r in x]):.2f} | {m([r['wasted_tokens'] for r in x]):.0f} | {m([r['gen_tokens'] for r in x]):.0f} | {m([r.get('judge_tokens',0) for r in x]):.1f} | {rate([bool(r['policy_viol']) for r in x]):.0f} |")
        P("\nPolicy catch rate (policy prompts: final delivered output has no violation OR was blocked) and FP rate (benign-suspicious blocked):\n")
        P("| setup | policy n | policy catch % | of which blocked by rail | benign n | FP block % |")
        P("|---|---|---|---|---|---|")
        for s in SETUPS:
            pol = [r for r in R if r["setup"] == s and r["path"] == "policy"]; be = [r for r in R if r["setup"] == s and r["path"] == "benign_susp"]
            if not pol: continue
            catch = [(r["blocked"] or not r["policy_viol"]) for r in pol]
            P(f"| {s} | {len(pol)} | {rate(catch):.0f} | {rate([r['blocked'] for r in pol]):.0f} | {len(be)} | {rate([r['blocked'] for r in be]):.0f} |")
        P("\nFailure penalty (wrong-path mean latency minus correct-path mean latency, same setup) and overhead vs baseline on correct path:\n")
        P("| setup | correct mean s | wrong mean s | penalty s | correct overhead vs baseline s | wrong-path mean wasted tok |")
        P("|---|---|---|---|---|---|")
        bc = m([r["latency"] for r in R if r["setup"] == "baseline" and r["path"] == "correct"])
        for s in SETUPS:
            c = [r["latency"] for r in R if r["setup"] == s and r["path"] == "correct"]; w = [r for r in R if r["setup"] == s and r["path"] == "wrong"]
            if not c or not w: continue
            P(f"| {s} | {m(c):.1f} | {m([r['latency'] for r in w]):.1f} | {m([r['latency'] for r in w]) - m(c):+.1f} | {m(c) - bc:+.1f} | {m([r['wasted_tokens'] for r in w]):.0f} |")
open("tables.md", "w").write("\n".join(out)); print("\n".join(out))
