#!/usr/bin/env bash
# P106B_Stage3sWa_generation_path_audit: expected 0.25h. Four fixed parent/student checkpoints, paired QA/ChatML and cache on/off, no training or teacher. 128 cases, hard900 seconds.
# New stage, immutable originals. No interactive input; every prerequisite stops this launcher.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3sWa_generation_path_audit.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3sWa_generation_path_audit --num 101 --note 'Four fixed parent/student checkpoints, paired QA/ChatML and cache on/off, no training or teacher. 128 cases, hard900 seconds.'
"$python_bin" scripts/runlog.py --name P106B_Stage3sWa_generation_path_audit --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_generation_path_audit.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3sWa_generation_path_audit --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_generation_path_audit.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3sWa_generation_path_audit --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_generation_path_audit.py --execute

