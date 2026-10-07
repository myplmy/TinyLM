#!/usr/bin/env bash
# CPU fixtures: explicit producer SIMPLE/STRUCTURED/UNKNOWN, shared3 structural attempts, real wrapper/mask/raw trace. No model/GPU/HF inputs.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4iWe_output_dispatch_cpu"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWe_output_dispatch_cpu --num 101 --note 'CPU fixtures: explicit producer SIMPLE/STRUCTURED/UNKNOWN, shared3 structural attempts, real wrapper/mask/raw trace. No model/GPU/HF inputs.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWe_output_dispatch_cpu --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_gemma_output_contract scripts.test_p106b_gemma_task_contract scripts.test_p106b_gemma_deficit
