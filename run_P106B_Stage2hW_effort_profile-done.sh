#!/usr/bin/env bash
# P106B Stage2hW: bounded teacher-only none/low/medium rate profile.
# Four pinned questions, 12 requests, same tagged prompt/sampler/seed/cap.
# Full-GPU Prism teacher, hard wall 17 min; student/data training 0.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2hW_effort_profile.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2hW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2hW_effort_profile --num 101 --note \
  'Authorized bounded CPU+GPU teacher probe. Server --reasoning auto, request efforts none/low/medium; same four source pairs, tagged prompt, thinking sampler, seed and max2048. Raw reasoning/final goes to new ignored v9.'
"$python_bin" scripts/runlog.py --name P106B_Stage2hW_effort_profile --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_effort_profile.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2hW_effort_profile --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_effort_profile.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2hW_effort_profile --num 101 --note \
  'Read: completion tokens include hidden reasoning; request wall includes HTTP and first-call effects. Unsupported or truncated arms remain negative evidence. No teacher answer truth or 5-step student rate claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2hW_effort_profile --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_effort_profile.py --execute
