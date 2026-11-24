#!/usr/bin/env bash
# Same selected9/layer budget, six MAG/absolute-gain/gradient-cost supports.
# About10-25min,4GiB free. Existing ratio/random and original168 values reused.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_support check; fi
"$python_bin" -B -m scripts.diag_p108b_support check || exit $?
timeout --signal=TERM --kill-after=20s 5460s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage25We_sparse_utility_controls --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_support actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage25We_sparse_utility_controls --num 108 --note "Final sparse-utility exit=$result. Compare selected count and real FP32 net norm, predicted/actual objective, DEV and all164 answers. Six independent global states are restored. Do not treat a score or one answer as general-quality evidence."
exit "$result"
