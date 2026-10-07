#!/usr/bin/env bash
# User CPU0.02h estimate; exactGemma Q4_0 target/Q8_0 assistant,b11396 libraries.
# Full file hashes and bounded headers; no server/model/GPU/downloads/student.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6cW_gemma12b_asset_contract.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage6cW_gemma12b_asset_contract --num 101 --note 'User CPU0.02h estimate; specifiedGemma target/assistant and llama-b11396 identity/header/projection contract. No server/model/GPU/downloads/student. Whole hashes do not prove role quality.'
"$python_bin" scripts/runlog.py --name P106B_Stage6cW_gemma12b_asset_contract --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_teacher_gate.py --mode assets --execute
