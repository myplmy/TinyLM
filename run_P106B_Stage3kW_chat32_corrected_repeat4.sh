#!/usr/bin/env bash
# P106B_Stage3kW_chat32_corrected_repeat4: user-run only. Expected 0.75h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3kW_chat32_corrected_repeat4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing runlog preserved: %s. Use a new stage on retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 --note \
  'B education: existing dense14 chat32 parent, corrected shared split, exactly4 passes, micro8/accum16 cap and checkpoint ON, Muon RMS4 LR0.0001. Short final groups are not refilled. Save new child checkpoint and parent/child fixed bilingual answers, up to3 attempts and native val-text/full-val forgetting. Cross-tokenizer CE ranking prohibited. Hard2h, pseudo pilot only.'
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_generate_chat_stops.py
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode train-b
"$python_bin" scripts/runlog.py --name P106B_Stage3kW_chat32_corrected_repeat4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode train-b
