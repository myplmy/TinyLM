#!/usr/bin/env bash
# User GPU0.5h estimate. Complete new4epoch child/parent/data SHA;36+36 actual firstanswers/3turn/language loss. Collection complete is not general intelligence PASS. Old eval outputs preserved.
# User-run only; no stdin/download. Exit8 prerequisite/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4mWc_literal_multiaxis"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4mWc_literal_multiaxis --num 101 --note 'User GPU0.5h estimate. Complete new4epoch child/parent/data SHA;36+36 actual firstanswers/3turn/language loss. Collection complete is not general intelligence PASS. Old eval outputs preserved.'
"$python_bin" scripts/runlog.py --name P106B_Stage4mWc_literal_multiaxis --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode eval --execute
