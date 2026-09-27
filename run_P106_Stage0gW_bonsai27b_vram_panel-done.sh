#!/usr/bin/env bash
# P106 Stage0gW: same GGUF and fork, sampled GPU16 versus full GPU memory.
# User explicitly authorized only this bounded CPU/GPU test in this task.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0gW_bonsai27b_vram_panel --num 098 --note \
  'P106 technical memory panel: same local PTQ1_0/Prism, hybrid16 then full GPU, ctx512/output64, each120s cap. In-process 0.2s NVML samples; no concurrent TinyLM training.'
"$python_bin" scripts/runlog.py --name P106_Stage0gW_bonsai27b_vram_panel --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0gW_bonsai27b_vram_panel --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 16
"$python_bin" scripts/runlog.py --name P106_Stage0gW_bonsai27b_vram_panel --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all
