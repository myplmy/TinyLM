#!/usr/bin/env bash
# User GPU0.50h max30min. Same parent/new full4epoch child72 firstanswers.
# Completed exact300M education required; no teacher/retraining/stdin/download.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4mW_gemma_capability_multiaxis"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4mW_gemma_capability_multiaxis --num 101 --note 'User GPU0.50h/max30min; completed same75M four actualepochs and child/parent/tokenizer/source hashes required. Same24 singles/four3turn episodes,72firstanswers; collect actual replies and stop reasons,no retries/teacher/retraining. Exactquestion overlap index and semantic truth separate,collection success is not intelligence PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage4mW_gemma_capability_multiaxis --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode eval --execute
