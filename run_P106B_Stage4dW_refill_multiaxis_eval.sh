#!/usr/bin/env bash
# User GPU posthoc parent/full4pass child first answers:24single and4three-turn episodes per model.
# Estimate0.25h, max30min. Existing4epoch training unchanged; no teacher or checkpoint writes.
# A missing full child is HOLD8 before model loading; no input prompts, retries or silent truncation.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dW_refill_multiaxis_eval.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4dW_refill_multiaxis_eval --num 101 --note 'After exact full4pass child: parent and student each24single plus4live3turn episodes, max72firstanswers. Contract checks differ from manual semantics. No teacher, retraining, retries or checkpoint writes; max30min.'
"$python_bin" scripts/runlog.py --name P106B_Stage4dW_refill_multiaxis_eval --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_refill_multiaxis.py --execute
