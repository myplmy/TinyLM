#!/usr/bin/env bash
# User GPU0.25h/max40min; Wb rejected a derived config property. New v3 only.
# Existing logs/outputs stay immutable; no stdin/download/teacher-owned JSON.
# New smoke first. Exit8 is gate-negative/HOLD,9 is tool failure.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eWc_saved_epoch_cfg_geometry.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4eWc_saved_epoch_cfg_geometry --num 101 --note 'User GPU0.25h/max40min; restore real serializedTMTConfig geometry,not missing derived n_layers key. Same5 endpoints/108new72carried/native5; failedv1/v2 preserved,no train/teacher/checkpoint writes. Read actual phase/error/row counts; new smoke first.'
"$python_bin" scripts/runlog.py --name P106B_Stage4eWc_saved_epoch_cfg_geometry --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_epoch_geometry_recovery.py --execute
