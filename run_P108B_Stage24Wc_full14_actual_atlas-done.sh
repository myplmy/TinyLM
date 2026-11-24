#!/usr/bin/env bash
# Full14 actual weight atlas; one global matrix per complete164-question set.
# About20-50min,4GiB free; original/frozen168values reused, no new training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -m scripts.diag_p108b_geometry check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wc_full14_actual_atlas --num 108 --note 'Nov16 directive140 before13KST. Reuse168 values; global body optimizer/value optimizer/CP writes0. All14 actual single-layer writes use equal absolute norm, with lower-common5pct panel explicitly labelled if legacy norm is infeasible. Full-path gradient and central differences precede actual results. Source68 reused; dev96 new; final192 sealed. Preserve each actual matrix packet/afterSHA and all164 answers per layer. Read predicted/actual/protection/fluency separately; one metric cannot establish general improvement.'
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wc_full14_actual_atlas --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_geometry actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wc_full14_actual_atlas --num 108 --note "Final full14 atlas exit=$result. Validate14 reports/physical budget/original restoration/CUDA and raw answers; select on DEV and freeze before FINAL."
exit "$result"
