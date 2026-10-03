#!/usr/bin/env bash
# P106C B: user GPU only; frozen A path gate, paired/color/token matched policies.
# Two policies share8/16/32 boundaries; report parent CE drift, max1800s.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage6W_balanced_early_policy_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage6W_balanced_early_policy_pair --num 102 --note 'User-run B only; A path gate must pass; same frozen train facts and fresh parent, micro8/accum4/ckpt-on.8/16/32 common boundaries, report parent loss drift,1800s cap; no automatic adoption.'
"$python_bin" scripts/runlog.py --name P106C_Stage6W_balanced_early_policy_pair --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_followup.py
"$python_bin" scripts/runlog.py --name P106C_Stage6W_balanced_early_policy_pair --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_replay.py
"$python_bin" scripts/runlog.py --name P106C_Stage6W_balanced_early_policy_pair --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_balanced_policy.py --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage6W_balanced_early_policy_pair --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_balanced_policy.py --execute
