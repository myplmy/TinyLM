#!/usr/bin/env bash
# P106B_Stage5eW_stage_receipt_contract: CPU three-stage receipt contract,0.05h. Synthetic COMPLETE/HOLD/ERROR fixtures only; GPU/model/training0.
# User execution only. Every phase and one final verdict share the runlog.
# Missing prerequisites stop dependent execution; no stdin/pause.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage5eW_stage_receipt_contract.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage5eW_stage_receipt_contract --num 101 --note 'CPU three-stage receipt contract,0.05h. Synthetic COMPLETE/HOLD/ERROR fixtures only; GPU/model/training0. Read EXPERIMENT_FINAL, not just an intermediate child exit0/file size.'
"$python_bin" scripts/runlog.py --name P106B_Stage5eW_stage_receipt_contract --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_stage_receipt.py --name P106B_Stage5eW_stage_receipt_contract --mode contract --execute
