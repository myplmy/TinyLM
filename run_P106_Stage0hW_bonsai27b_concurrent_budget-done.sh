#!/usr/bin/env bash
# P106 Stage0hW: intermediate GPU layer counts, teacher alone; estimate only.
# No TinyLM trainer is launched or modified by this diagnostic.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0hW_bonsai27b_concurrent_budget --num 098 --note \
  'P106 same SHA/Prism ctx512/output64 teacher-alone VRAM+decode panel at GPU40,48,56. Compare sampled global memory against P076 student reserved separately; simultaneous model run NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106_Stage0hW_bonsai27b_concurrent_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0hW_bonsai27b_concurrent_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 40
"$python_bin" scripts/runlog.py --name P106_Stage0hW_bonsai27b_concurrent_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 48
"$python_bin" scripts/runlog.py --name P106_Stage0hW_bonsai27b_concurrent_budget --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 56
