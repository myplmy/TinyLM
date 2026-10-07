#!/usr/bin/env bash
# User GPU two optimizer updates/256 row exposures from completed same75M corpus,original chat32 parent/micro8 accum16 checkpointON/currentLR. Teacher must be down. Actual counts/masks/native/answers separate,no300M claim.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4k0W_gemma_student_wire"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4k0W_gemma_student_wire --num 101 --note 'User GPU two optimizer updates/256 row exposures from completed same75M corpus,original chat32 parent/micro8 accum16 checkpointON/currentLR. Teacher must be down. Actual counts/masks/native/answers separate,no300M claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage4k0W_gemma_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode wire --execute
