#!/usr/bin/env bash
# CPU/tokenizer only. Frozen28 source pairs,three matched exposure schedules.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_correction_course --check-only; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage37Wc_correction_course_contract_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_correction_course
exit $?
