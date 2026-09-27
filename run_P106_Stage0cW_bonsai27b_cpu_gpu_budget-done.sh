#!/usr/bin/env bash
# P106 Stage0cW: one bounded local CPU versus 16-layer CUDA offload probe.
# The current user explicitly authorized this CPU+GPU technical test only.
# No teacher dataset, training, download or protected data is touched.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
cli_path=/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe/llama-cli
model_path="$repo_root/HF/models--prism-ml--Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf"
prompt='Answer the arithmetic question 2+2. State the result as one digit.'

"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 --note \
  "P106 bounded technical runtime only: same published SHA/Prism build, CPU ngl0 then CUDA ngl16; ctx512, 64 output tokens, each timeout180s. No quality or concurrent-training claim."
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py

if [[ ! -x "$cli_path" || ! -f "$model_path" ]]; then
  echo '[FAIL] exact Prism CLI or model is missing; no runtime arm started'
  exit 9
fi

"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 --note \
  'CPU-only arm: ngl0; CUDA backend may initialize, but no model layers are offloaded.'
cpu_rc=0
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  timeout -s TERM -k 5s 180s "$cli_path" --model "$model_path" \
  --gpu-layers 0 --ctx-size 512 --n-predict 64 --threads 8 \
  --batch-size 64 --ubatch-size 64 --flash-attn auto \
  --reasoning-effort medium --reasoning-budget 16 \
  --temp 0 --top-p 1 --top-k 0 --min-p 0 \
  --no-display-prompt --single-turn --no-warmup --prompt "$prompt" || cpu_rc=$?
if [[ "$cpu_rc" -ne 0 ]]; then
  echo "[FAIL] CPU-only arm exit=$cpu_rc; GPU arm not started"
  exit 9
fi

free_mib="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | sed -n '1p' | tr -d '[:space:]')"
if [[ ! "$free_mib" =~ ^[0-9]+$ || "$free_mib" -lt 8192 ]]; then
  echo "[HOLD] GPU free VRAM must be at least 8192 MiB; observed=$free_mib"
  exit 8
fi
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 --note \
  "CUDA hybrid arm: ngl16 with GPU free=${free_mib}MiB before launch; this is NOT simultaneous TinyLM training."
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
gpu_rc=0
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  env CUDA_VISIBLE_DEVICES=0 timeout -s TERM -k 5s 180s "$cli_path" --model "$model_path" \
  --gpu-layers 16 --ctx-size 512 --n-predict 64 --threads 8 \
  --batch-size 64 --ubatch-size 64 --flash-attn auto \
  --reasoning-effort medium --reasoning-budget 16 \
  --temp 0 --top-p 1 --top-k 0 --min-p 0 \
  --no-display-prompt --single-turn --no-warmup --prompt "$prompt" || gpu_rc=$?
"$python_bin" scripts/runlog.py --name P106_Stage0cW_bonsai27b_cpu_gpu_budget --num 098 -- \
  nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
if [[ "$gpu_rc" -ne 0 ]]; then
  echo "[FAIL] CUDA hybrid arm exit=$gpu_rc; preserve the log and do not infer backend PASS"
  exit 9
fi
echo '[COLLECTED] CPU and hybrid process exits are 0; confirm generated tokens and actual offloaded layers from the log before PASS.'
