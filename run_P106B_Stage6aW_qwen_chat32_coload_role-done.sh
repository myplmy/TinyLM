#!/usr/bin/env bash
# Purpose: pinned Qwen role answers, then actual chat32 dense8x16 checkpointON coload.
# Budget: at most20min, one synthetic optimizer update, no saved checkpoint.
# New evidence only; model/quality adoption is not implied. No interactive input.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6aW_qwen_chat32_coload_role.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_qwen_teacher || exit 9
"$python_bin" scripts/runlog.py --name P106B_Stage6aW_qwen_chat32_coload_role --num 101 --note 'Bounded20min Qwen role4 and real chat32 dense micro8 accum16 checkpointON seq1024 one synthetic update. Read raw teacher answers and QWEN_GATE_FINAL. No saved checkpoint or formal SFT.'
"$python_bin" scripts/runlog.py --name P106B_Stage6aW_qwen_chat32_coload_role --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_qwen_coload.py --execute
