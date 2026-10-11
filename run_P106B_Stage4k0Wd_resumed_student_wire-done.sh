#!/usr/bin/env bash
# User GPU0.5h estimate after same completedV4 corpus and teacher down. Originalparent chat32 micro8 accum16 checkpointON currentLR two updates. Prior wire never allocated a model; not concurrent or300M evidence.
# User-run only; no stdin/download. Exit8 is prerequisite/partial,9 error,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4k0Wd_resumed_student_wire"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4k0Wd_resumed_student_wire --num 101 --note 'User GPU0.5h estimate after same completedV4 corpus and teacher down. Originalparent chat32 micro8 accum16 checkpointON currentLR two updates. Prior wire never allocated a model; not concurrent or300M evidence.'
"$python_bin" scripts/runlog.py --name P106B_Stage4k0Wd_resumed_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode wire --execute
