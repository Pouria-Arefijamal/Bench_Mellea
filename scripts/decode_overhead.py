"""Constrained-decoding overhead (vLLM guided decoding via response_format json_schema) vs free generation."""
import json, sys, time, openai, common
OUTF = sys.argv[1]
cfgs = [(a.split(":")[0], a.split(":")[1], int(a.split(":")[2])) for a in sys.argv[2:]]
cl = openai.OpenAI(base_url=common.ollama_v1(), api_key="EMPTY", timeout=1800)
out = []
for model, size, reps in cfgs:
    item = [p for p in common.build_prompts(size) if p["id"] == "c0"][0]
    cl.chat.completions.create(model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=1)
    for rep in range(reps):
        for mode in ("free", "schema"):
            kw = {}
            if mode == "schema":
                kw["response_format"] = {"type": "json_schema", "json_schema": {"name": "Config", "schema": common.Config.model_json_schema(), "strict": True}}
            t0 = time.perf_counter(); ttft = None; txt = []; usage = None
            for ch in cl.chat.completions.create(model=model, messages=[{"role": "user", "content": item["prompt"]}], stream=True,
                    stream_options={"include_usage": True}, temperature=0.7, seed=rep, max_tokens=12000, **kw):
                if ch.usage: usage = ch.usage
                if ch.choices and ch.choices[0].delta.content:
                    if ttft is None: ttft = time.perf_counter() - t0
                    txt.append(ch.choices[0].delta.content)
            lat = time.perf_counter() - t0
            n = usage.completion_tokens
            cfg, err = common.parse_struct("".join(txt))
            r = dict(model=model, size=size, mode=mode, rep=rep, ttft=ttft, latency=lat, completion_tokens=n,
                     decode_ms_per_tok=(lat - ttft) * 1000 / max(n - 1, 1), prompt_tokens=usage.prompt_tokens,
                     struct_valid=cfg is not None, sem_correct=(cfg is not None and not common.semantic_errors(cfg, item["spec"])))
            out.append(r); print(r, flush=True)
json.dump(out, open(OUTF, "w"), indent=1)
