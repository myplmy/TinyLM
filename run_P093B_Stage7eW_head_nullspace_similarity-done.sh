#!/usr/bin/env bash
# Approved cause-diagnosis subcontrol120sec. Same12 final states: change nullspace cosine while preserving complete next-token logits. No generation/training/checkpoint.
# Estimated 0.04h; GPU=Y; hard120sec; no stdin/download/cleanup.
# New stage: full-state patching changes information as well as cosine.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage7eW_head_nullspace_similarity_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7eW_head_nullspace_similarity_"$run_stamp" --num 103 --note 'Approved cause-diagnosis subcontrol120sec. Same12 final states: change nullspace cosine while preserving complete next-token logits. No generation/training/checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7eW_head_nullspace_similarity_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_similarity_control.py --mode intervene --tag p093b_similarity_control_v1_s1337 --max-wall-sec 120 --execute
