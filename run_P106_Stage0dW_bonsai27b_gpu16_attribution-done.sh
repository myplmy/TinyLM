#!/usr/bin/env bash
# P106 Stage0dW: bounded verbose GPU16 attribution after Stage0c produced output
# but its compact llama-cli UI omitted the actual offload/buffer evidence.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
cli_path=/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe/llama-cli
model_path="$repo_root/HF/models--prism-ml--Ternary-Bonsai-2-27B-gguf/Ternary-Bonsai-2-27B-PTQ1_0.gguf"

"$python_bin" scripts/runlog.py --name P106_Stage0dW_bonsai27b_gpu16_attribution --num 098 --note \
  'P106 CUDA16 attribution only: verbose info plus simple IO, offline, ctx512, output16, timeout120s. Confirm offloaded layers and GPU buffers; exit0 alone is insufficient.'
"$python_bin" scripts/runlog.py --name P106_Stage0dW_bonsai27b_gpu16_attribution --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_bonsai_assets.py --check-only
if [[ ! -x "$cli_path" || ! -f "$model_path" ]]; then
  echo '[FAIL] exact Prism CLI or model missing'
  exit 9
fi
free_mib="$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | sed -n '1p' | tr -d '[:space:]')"
if [[ ! "$free_mib" =~ ^[0-9]+$ || "$free_mib" -lt 8192 ]]; then
  echo "[HOLD] GPU free VRAM must be >=8192MiB; observed=$free_mib"
  exit 8
fi
"$python_bin" scripts/runlog.py --name P106_Stage0dW_bonsai27b_gpu16_attribution --num 098 --note \
  "GPU free before model=${free_mib}MiB; no simultaneous TinyLM training is claimed."
"$python_bin" scripts/runlog.py --name P106_Stage0dW_bonsai27b_gpu16_attribution --num 098 -- \
  env CUDA_VISIBLE_DEVICES=0 timeout -s TERM -k 5s 120s "$cli_path" \
  --offline --simple-io --verbosity 3 --model "$model_path" \
  --gpu-layers 16 --ctx-size 512 --n-predict 16 --threads 8 \
  --batch-size 64 --ubatch-size 64 --flash-attn auto \
  --reasoning-effort medium --reasoning-budget 8 \
  --temp 0 --top-p 1 --top-k 0 --min-p 0 \
  --no-display-prompt --single-turn --no-warmup \
  --prompt 'Answer 2+2 as one digit.'
"$python_bin" scripts/runlog.py --name P106_Stage0dW_bonsai27b_gpu16_attribution --num 098 -- \
  nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
echo '[COLLECTED] Verify actual CUDA layer count and GPU model/KV/compute buffers in the log before PASS.'
