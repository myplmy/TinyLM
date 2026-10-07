#!/usr/bin/env bash
# User GPU0.25h/max40min; same5 endpoints,108 new answers/72 carried and native5.
# Fixed carried model-key attribution; v1 failure preserved, new v2 output only.
# No stdin, teacher, training or checkpoint writes. Collection is not quality PASS.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eWb_saved_epoch_row_attribution.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4eWb_saved_epoch_row_attribution --num 101 --note 'User GPU0.25h/max40min; same5 endpoints/108 new answers/72 carried/native5. Fixed row attribution; failed v1 preserved/new v2. Read phase/error and actual vs planned rows. No teacher/train/checkpoint writes; new smoke first.'
"$python_bin" scripts/runlog.py --name P106B_Stage4eWb_saved_epoch_row_attribution --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_epoch_retention_recovery.py --execute
