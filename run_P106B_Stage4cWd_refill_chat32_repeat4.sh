#!/usr/bin/env bash
# User-run conditional12h estimate; newv3 actual75M KO50EN50 fourpasses; matching two-update wire required; no teacher resident.
# No interactive input. Prior logs/outputs are preserved; new stage needed to retry.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cWd_refill_chat32_repeat4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4cWd_refill_chat32_repeat4 --num 101 --note 'User-run conditional12h estimate; newv3 actual75M KO50EN50 fourpasses; matching two-update wire required; no teacher resident. Read final report and exact input hashes. Technical completion is not semantic quality or scientific adoption.'
"$python_bin" scripts/runlog.py --name P106B_Stage4cWd_refill_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --mode new-refill --execute
