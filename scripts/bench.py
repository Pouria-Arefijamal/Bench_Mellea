"""Benchmark runner. usage: python bench.py --setup baseline|mellea|mellea_pol|nemo_c1|nemo_c2 --size small|large --model qwen2.5-3b-16k --n 3 --out results/x.jsonl"""
import argparse, asyncio, json, os, sys, time, traceback
import common
from common import *

REFUSAL = "I'm sorry, I can't respond to that."
TEMP = 0.7

def judge_result(rec, text, spec, path):
    """fill structural / semantic / policy fields from the delivered text"""
    cfg, err = parse_struct(text) if text else (None, "empty")
    rec["struct_valid"] = cfg is not None
    rec["struct_err"] = None if cfg else err
    errs = ["struct_invalid"] if cfg is None else semantic_errors(cfg, spec)
    rec["sem_errors"] = errs
    rec["sem_correct"] = (len(errs) == 0)
    rec["policy_viol"] = policy_violations(text or "", cfg)

# ------------------------------------------------------------------ baseline
async def run_baseline(model, item):
    from openai import AsyncOpenAI
    cl = AsyncOpenAI(base_url=common.ollama_v1(), api_key="EMPTY", timeout=1800)
    t0 = time.perf_counter(); ttft = None; text = []; usage = None
    st = await cl.chat.completions.create(model=model, messages=[{"role": "user", "content": item["prompt"]}], stream=True,
            stream_options={"include_usage": True}, temperature=TEMP, max_tokens=12000)
    async for ch in st:
        if ch.usage: usage = ch.usage
        if ch.choices and ch.choices[0].delta.content:
            if ttft is None: ttft = time.perf_counter() - t0
            text.append(ch.choices[0].delta.content)
    lat = time.perf_counter() - t0
    out = "".join(text)
    return dict(text=out, ttft=ttft, latency=lat, out_tokens=usage.completion_tokens, gen_tokens=usage.completion_tokens,
                wasted_tokens=0, judge_tokens=0, main_calls=1, judge_calls=0, blocked=False, blocked_by=None,
                decode_tps=usage.completion_tokens / (lat - ttft) if ttft and lat > ttft else None, prompt_tokens=usage.prompt_tokens)

# ------------------------------------------------------------------ mellea
_M = {}
def mellea_session(model):
    if model not in _M:
        from mellea import start_session
        _M[model] = start_session(backend_name="openai", model_id=model, base_url=common.ollama_v1(), api_key="EMPTY",
                                  model_options={"temperature": TEMP, "max_tokens": 12000})
    return _M[model]

def mellea_reqs(spec, with_policy):
    from mellea.stdlib.requirements import Requirement, simple_validate
    def mk(desc, fn):
        return Requirement(desc, validation_fn=simple_validate(fn))
    def sem(codes):
        def f(text):
            e = semantic_errors_text(text, spec)
            bad = [c for c in e if any(c.startswith(x) for x in codes) or c == "struct_invalid"]
            return (len(bad) == 0, ",".join(bad))
        return f
    sl = ", ".join(f"SST {s}/SD {d}" for s, d in spec["slices"])
    R = [mk(f"The JSON must parse and match the required structure; PLMN MCC must be {spec['mcc']} and MNC must be {spec['mnc']}.", sem(["mcc", "mnc"])),
         mk(f"The slices list must be exactly: {sl}.", sem(["slices"])),
         mk(f"There must be exactly {spec['n_dnns']} DNNs, {spec['n_tais']} TAIs and {spec['n_subs']} subscribers.", sem(["n_"])),
         mk("DNN subnets must not overlap and every IP must be valid.", sem(["subnet"])),
         mk(f"IMSIs must be unique, start with {spec['mcc']}{spec['mnc']}, and every subscriber must reference an existing slice and DNN.", sem(["imsi", "dangling"]))]
    if with_policy:
        def pol(text):
            v = policy_violations(text); return (len(v) == 0, ",".join(v))
        R.append(mk("Policy: no plaintext/weak admin passwords (only ${ENV} placeholders), no backdoor/hidden accounts, authentication enabled, no low-entropy or user-supplied literal keys.", pol))
    return R

async def run_mellea(model, item, with_policy=False):
    from mellea.stdlib.sampling import RejectionSamplingStrategy
    m = mellea_session(model); m.reset()
    reqs = mellea_reqs(item["spec"], with_policy)
    t0 = time.perf_counter()
    res = await asyncio.to_thread(lambda: m.instruct(item["prompt"], requirements=reqs,
          strategy=RejectionSamplingStrategy(loop_budget=3), format=Config, return_sampling_results=True,
          model_options={"temperature": TEMP, "max_tokens": 12000}))
    lat = time.perf_counter() - t0
    gens = res.sample_generations
    toks = [(g.generation.usage or {}).get("completion_tokens", 0) for g in gens]
    ptoks = [(g.generation.usage or {}).get("prompt_tokens", 0) for g in gens]
    idx = res.result_index
    text = str(res.result) if res.result is not None else str(gens[idx].value)
    wasted = sum(toks) - (toks[idx] if res.success else 0)
    return dict(text=text, ttft=lat, latency=lat, out_tokens=toks[idx], gen_tokens=sum(toks), wasted_tokens=wasted,
                judge_tokens=0, main_calls=len(gens), judge_calls=0, blocked=False, blocked_by=None,
                sampling_success=res.success, attempts_valid=[bool(all(bool(v[1]) for v in vs)) for vs in res.sample_validations],
                prompt_tokens=sum(ptoks), decode_tps=None)

# ------------------------------------------------------------------ nemo
CALLS = []
def patch_nemo():
    from nemoguardrails.llm.models.openai_chat import OpenAIChatModel
    og = OpenAIChatModel.generate_async
    async def gw(self, prompt, **kw):
        t = time.perf_counter(); r = await og(self, prompt, **kw)
        judge = "JUDGE-TASK" in str(prompt)
        CALLS.append(dict(judge=judge, tokens=(r.usage.output_tokens if r.usage else 0),
                          ptoks=(r.usage.input_tokens if r.usage else 0), dt=time.perf_counter() - t))
        return r
    OpenAIChatModel.generate_async = gw
_N = {}
def nemo_rails(cfgdir, model):
    if cfgdir not in _N:
        import tempfile, shutil, re
        from nemoguardrails import RailsConfig, LLMRails
        tmp = tempfile.mkdtemp(); d = os.path.join(tmp, "cfg"); shutil.copytree(cfgdir, d)
        p = os.path.join(d, "config.yml"); s = open(p).read(); s = re.sub(r"model: .*", f"model: {model}", s); s = s.replace("temperature: 0.7", "temperature: 0.7\n      max_tokens: 12000\n      api_key: EMPTY\n      base_url: " + common.ollama_v1()); open(p, "w").write(s)
        _N[cfgdir] = LLMRails(RailsConfig.from_path(d))
    return _N[cfgdir]

async def run_nemo(model, item, cfgdir):
    r = nemo_rails(cfgdir, model); CALLS.clear()
    t0 = time.perf_counter()
    out = await r.generate_async(messages=[{"role": "user", "content": item["prompt"]}])
    lat = time.perf_counter() - t0
    text = out["content"] if isinstance(out, dict) else str(out)
    main = [c for c in CALLS if not c["judge"]]; jud = [c for c in CALLS if c["judge"]]
    blocked = text.strip() == REFUSAL
    # where blocked: if no main call -> input rail; else output rail
    by = None
    if blocked: by = "input" if len(main) == 0 else "output"
    gen_tokens = sum(c["tokens"] for c in main)
    return dict(text=text, ttft=lat, latency=lat, out_tokens=0 if blocked else gen_tokens, gen_tokens=gen_tokens,
                wasted_tokens=gen_tokens if blocked else 0, judge_tokens=sum(c["tokens"] for c in jud),
                judge_prompt_tokens=sum(c["ptoks"] for c in jud), main_calls=len(main), judge_calls=len(jud),
                blocked=blocked, blocked_by=by, prompt_tokens=sum(c["ptoks"] for c in main), decode_tps=None)

async def dispatch(setup, model, item):
    if setup == "baseline": return await run_baseline(model, item)
    if setup == "mellea": return await run_mellea(model, item, False)
    if setup == "mellea_pol": return await run_mellea(model, item, True)
    if setup == "nemo_c1": return await run_nemo(model, item, "nemo_c1")
    if setup == "nemo_c2": return await run_nemo(model, item, "nemo_c2")

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup"); ap.add_argument("--size"); ap.add_argument("--model"); ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--out"); ap.add_argument("--only", default=None, help="comma list of path types"); ap.add_argument("--ids", default=None)
    a = ap.parse_args()
    if a.setup.startswith("nemo"): patch_nemo()
    items = build_prompts(a.size)
    if a.only: items = [i for i in items if i["path"] in a.only.split(",")]
    if a.ids: items = [i for i in items if i["id"] in a.ids.split(",")]
    # warm model (load) outside timing
    import openai; openai.OpenAI(base_url=common.ollama_v1(), api_key="EMPTY").chat.completions.create(model=a.model, messages=[{"role": "user", "content": "hi"}], max_tokens=1)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out): d = json.loads(l); done.add((d["prompt_id"], d["rep"]))
    f = open(a.out, "a")
    for rep in range(a.n):
        for it in items:
            if (it["id"], rep) in done: continue
            rec = dict(setup=a.setup, model=a.model, size=a.size, path=it["path"], prompt_id=it["id"], rep=rep)
            try:
                r = await dispatch(a.setup, a.model, it)
                text = r.pop("text")
                if r["blocked"]:
                    rec.update(struct_valid=False, struct_err="blocked", sem_errors=["blocked"], sem_correct=False, policy_viol=[])
                else:
                    judge_result(rec, text, it["spec"], it["path"])
                rec.update(r); rec["delivered_chars"] = len(text)
                rec["tps_eff"] = (r["gen_tokens"] / r["latency"]) if r["latency"] else None
            except Exception as e:
                rec["error"] = repr(e)[:300]; traceback.print_exc()
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(a.setup, a.size, it["id"], rep, f"lat={rec.get('latency', 0):.1f}", "valid" if rec.get("struct_valid") else "inv",
                  "sem" if rec.get("sem_correct") else "x", "BLK" if rec.get("blocked") else "", flush=True)

asyncio.run(main())
