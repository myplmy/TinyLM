#!/usr/bin/env bash
# User GPU7-12min/max60min. Same original16/seed/Gemma MTPoff/card budgets; literal learner request in DATA and code-owned JSON change-turn. FreshV3; strict16 remains until explicit new policy. Prior complex4 SHA preserved, not newly executed.
# User-run only; no stdin/download. Exit8 prerequisite/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4iWi_literal_learner_contract16"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWi_literal_learner_contract16 --num 101 --note 'User GPU7-12min/max60min. Same original16/seed/Gemma MTPoff/card budgets; literal learner request in DATA and code-owned JSON change-turn. FreshV3; strict16 remains until explicit new policy. Prior complex4 SHA preserved, not newly executed.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWi_literal_learner_contract16 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode contract16 --execute
