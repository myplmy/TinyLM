#!/usr/bin/env bash
# User CPU estimate0.5h; exact75M train/KOEN/QA-JSON-multiturn/val/family caps before publishing V3. No student; shortage HOLD8. Original C, old V1/V2 roots preserved.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4kWb_gemma_output_completed_corpus"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4kWb_gemma_output_completed_corpus --num 101 --note 'User CPU estimate0.5h; exact75M train/KOEN/QA-JSON-multiturn/val/family caps before publishing V3. No student; shortage HOLD8. Original C, old V1/V2 roots preserved.'
"$python_bin" scripts/runlog.py --name P106B_Stage4kWb_gemma_output_completed_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_output_recovery.py --mode finalize --execute
