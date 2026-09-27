#!/usr/bin/env bash
# P106 Stage0oW: isolate student's microbatch peak with FFN32 fused teacher.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0oW_bonsai27b_p076_micro4_coload --num 098 --note \
  'FFN32 GDN-fused teacher plus same P076 architecture/optimizer synthetic 1-step with micro_bs4. Full trainer accum32/compiled/parent quality and speed are NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106_Stage0oW_bonsai27b_p076_micro4_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_coload.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0oW_bonsai27b_p076_micro4_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_coload.py --placement ffn32 --micro-bs 4
