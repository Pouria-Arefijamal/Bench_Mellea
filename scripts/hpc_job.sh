#!/bin/bash
#SBATCH --account=tecnun
#SBATCH --partition=general
#SBATCH --qos=gpu-regular
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --requeue
#SBATCH --open-mode=append
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96gb
# vLLM version. usage: sbatch --job-name=guard-7b --output=... hpc_job.sh <short> <ollama-tag> <profile>
set -uo pipefail
SHORT=$1; TAG=$2; PROFILE=$3
G=/scratch/parefijamal/guard
RUN=$G/runs/$SHORT; mkdir -p $RUN/results $RUN/logs $RUN/models
cd $G/code
echo "=== NODE $(hostname) $(date) ==="; nvidia-smi; nvidia-smi -L > $RUN/logs/nvidia-smi-L.txt; nvidia-smi > $RUN/logs/nvidia-smi.txt
lscpu | egrep "Model name|^CPU\(s\)" > $RUN/logs/cpu.txt
source /etc/profile.d/lmod.sh; module purge; module load Miniconda3/23.10.0-1
source "$(conda info --base)/etc/profile.d/conda.sh"
export HF_HOME=/scratch/parefijamal/fl_llm/hf HF_XET_HIGH_PERFORMANCE=1
VPY=/scratch/parefijamal/fl_llm/venv/bin/python; BPY=$G/venv/bin/python
export PATH=$G/venv/bin:$PATH
$VPY -c "import vllm;print('vllm',vllm.__version__)" > $RUN/logs/vllm_version.txt 2>&1
$VPY -c "import torch;print('torch',torch.__version__,torch.version.cuda)" >> $RUN/logs/vllm_version.txt 2>&1
$BPY -m pip list 2>/dev/null | egrep -i "^(mellea|nemoguardrails|openai|pydantic) " > $RUN/logs/versions.txt
PORT=$((20000 + RANDOM % 20000)); export LLM_BASE_URL=http://127.0.0.1:$PORT/v1
M=qwen2.5-$SHORT
EXTRA=""; [ -n "${QUANT:-}" ] && EXTRA="--quantization $QUANT"
$VPY -m vllm.entrypoints.openai.api_server --model $TAG --served-model-name $M --max-model-len 16384 \
   --gpu-memory-utilization 0.85 --disable-log-requests --host 127.0.0.1 --port $PORT $EXTRA > $RUN/logs/vllm_serve.log 2>&1 &
SP=$!
for i in $(seq 360); do curl -s $LLM_BASE_URL/models | grep -q "$M" && break; kill -0 $SP 2>/dev/null || { echo vLLM died; tail -30 $RUN/logs/vllm_serve.log; exit 1; }; sleep 5; done
curl -s $LLM_BASE_URL/models | head -c 300; echo
cd $G/code
run() { $BPY bench.py "$@" ; }
R=$RUN/results
case $PROFILE in
 full3|full7)   # SMALL n=3 all prompts, LARGE all 10 prompts
   NL=1; [ $PROFILE = full3 ] && NL=2
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size small --model $M --n 3 --out $R/${S}_small_$SHORT.jsonl > $RUN/logs/${S}_small.log 2>&1; done
   run --setup mellea_pol --size small --model $M --n 3 --only policy,benign_susp,correct --out $R/mellea_pol_small_$SHORT.jsonl > $RUN/logs/mellea_pol_small.log 2>&1
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size large --model $M --n $NL --out $R/${S}_large_$SHORT.jsonl > $RUN/logs/${S}_large.log 2>&1; done
   if [ $PROFILE = full7 ]; then
     $BPY stream_exp.py $M $R/stream_exp_$SHORT.json > $RUN/logs/stream_exp.log 2>&1
   fi
   ;;
 smoke)
   IDS=c0,w_same_subnet,p_backdoor,b_keys
   for S in baseline mellea mellea_pol nemo_c1 nemo_c2; do run --setup $S --size small --model $M --n 1 --ids $IDS --out $R/${S}_small_$SHORT.jsonl > $RUN/logs/${S}_small.log 2>&1; done
   $BPY stream_exp.py $M $R/stream_exp_$SHORT.json > $RUN/logs/stream_exp.log 2>&1
   ;;
 smoke2)
   $BPY stream_exp.py $M $R/stream_exp_$SHORT.json > $RUN/logs/stream_exp.log 2>&1
   ;;
 stream7)
   $BPY stream_exp.py $M $R/stream_exp_$SHORT.json > $RUN/logs/stream_exp.log 2>&1
   ;;
 mid14)  # SMALL n=2 all prompts, LARGE 6 prompts n=1
   LIDS=c0,c1,c2,w_same_subnet,p_backdoor,b_admin_dnn
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size small --model $M --n 2 --out $R/${S}_small_$SHORT.jsonl > $RUN/logs/${S}_small.log 2>&1; done
   run --setup mellea_pol --size small --model $M --n 2 --only policy,benign_susp,correct --out $R/mellea_pol_small_$SHORT.jsonl > $RUN/logs/mellea_pol_small.log 2>&1
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size large --model $M --n 1 --ids $LIDS --out $R/${S}_large_$SHORT.jsonl > $RUN/logs/${S}_large.log 2>&1; done
   ;;
 big32)  # SMALL n=1 all 26 prompts, LARGE 6 prompts n=1
   LIDS=c0,c1,c2,w_same_subnet,p_backdoor,b_admin_dnn
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size small --model $M --n 1 --out $R/${S}_small_$SHORT.jsonl > $RUN/logs/${S}_small.log 2>&1; done
   run --setup mellea_pol --size small --model $M --n 1 --only policy,benign_susp,correct --out $R/mellea_pol_small_$SHORT.jsonl > $RUN/logs/mellea_pol_small.log 2>&1
   for S in baseline mellea nemo_c1 nemo_c2; do run --setup $S --size large --model $M --n 1 --ids $LIDS --out $R/${S}_large_$SHORT.jsonl > $RUN/logs/${S}_large.log 2>&1; done
   ;;
esac
# decode overhead (constrained decoding) for this model
case $PROFILE in
 full3) DEC="$M:small:3 $M:large:2";;
 full7) DEC="$M:small:3 $M:large:2";;
 mid14) DEC="$M:small:3 $M:large:1";;
 big32) DEC="$M:small:2 $M:large:1";;
 stream7) DEC="$M:small:1";;
 smoke2) DEC="$M:small:1 $M:large:1";;
 smoke) DEC="$M:small:1";;
esac
$BPY decode_overhead.py $R/decode_overhead_$SHORT.json $DEC > $RUN/logs/decode_overhead.log 2>&1
kill $SP 2>/dev/null
echo DONE > $RUN/logs/DONE; date
