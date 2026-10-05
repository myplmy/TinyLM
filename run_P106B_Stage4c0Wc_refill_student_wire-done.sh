#!/usr/bin/env bash
# User-run GPU two-update wire on newv3 corpus only; micro8 accum16 checkpointON; no300M claim.
# No interactive input. Prior logs/outputs are preserved; new stage needed to retry.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4c0Wc_refill_student_wire.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wc_refill_student_wire --num 101 --note 'User-run GPU two-update wire on newv3 corpus only; micro8 accum16 checkpointON; no300M claim. Read final report and exact input hashes. Technical completion is not semantic quality or scientific adoption.'
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wc_refill_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --mode wire-refill --execute
