# Bench_Mellea

Benchmark of three ways to get a valid, policy-compliant 5G-core configuration from an LLM: plain call (baseline), [Mellea](https://mellea.ai) (grammar-constrained output plus rejection sampling), and NVIDIA NeMo Guardrails (rule-based C1 and LLM-judge C2 rails). Models Qwen2.5 3B/7B/14B/32B-AWQ served with vLLM on an A100-80GB.

Results, setup, caveats and source citations: [RESULTS.md](RESULTS.md). Raw per-request JSONL: `hpc_results/runs/*/results/`. Scripts: `scripts/` (`bench.py`, `hpc_job.sh` for the Slurm job, `make_results.py` for the tables). NeMo configs: `nemo_*`. Scripts expect to run from one directory with `nemo_*` beside them (copy `scripts/*` next to `nemo_*`).
`ollama_local_partial_sidenote/` holds partial earlier Jetson/Ollama rows and is not comparable.
