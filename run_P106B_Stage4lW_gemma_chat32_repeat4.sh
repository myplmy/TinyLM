#!/usr/bin/env bash
# User GPU estimated6-12h; completed75M and matching wire2 required. Original chat32 parent/micro8 accum16 checkpointON/LR1e-4 Muon4e-4,four actualepochs/300M,epoch checkpoints/native/actual answers. No teacher co-residency.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4lW_gemma_chat32_repeat4"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4lW_gemma_chat32_repeat4 --num 101 --note 'User GPU estimated6-12h; completed75M and matching wire2 required. Original chat32 parent/micro8 accum16 checkpointON/LR1e-4 Muon4e-4,four actualepochs/300M,epoch checkpoints/native/actual answers. No teacher co-residency.'
"$python_bin" scripts/runlog.py --name P106B_Stage4lW_gemma_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode train --execute
