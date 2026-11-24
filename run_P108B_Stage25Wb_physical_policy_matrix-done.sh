#!/usr/bin/env bash
# Physical NET-matched repeated/distributed/sparse edit comparison,18 arms.
# Original single9 is reused; other arms use frozen168 values and C0.
# Expected1-3hours,4GiB free. No training/aux updates/checkpoint overwrite.
# Dependent preflight failure stops this entry; all raw negative results stay.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -m scripts.diag_p108b_policy check
fi
"$python_bin" -B -m scripts.diag_p108b_policy check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage25Wb_physical_policy_matrix --num 108 --note 'Directive140 before13KST. All18 primary policies, SAME/SEQ/EQUAL/ADAPT distinct or revisit, n2/4 and selective/random supports. Original168 values/C0 frozen, no auxiliary/body optimizer. CommonNET13.882119348 is lower than old15.679. Progressive caps, actual FP32 norm/path/support, trial safeguards, raw164answers, ordered packets and rollback retained. Correct requested repetition protected; FINAL sealed.' || exit $?
timeout --signal=TERM --kill-after=20s 14460s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage25Wb_physical_policy_matrix --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_policy actual --arms SINGLE1 SAME2 SEQ2 EQUAL2 ADAPT_D2 ADAPT_R2 SAME4 SEQ4 EQUAL4 ADAPT_D4 ADAPT_R4 SINGLE1_SPARSE8 SINGLE1_SPARSE32 ADAPT_R4_SPARSE8 ADAPT_R4_SPARSE32 SINGLE1_RANDOM32_1337 SINGLE1_RANDOM32_2337 SINGLE1_RANDOM32_3337
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage25Wb_physical_policy_matrix --num 108 --note "Final policy exit=$result. Inspect actual net versus path and undersaturation; source/core/packets/protection/DEV/raw language must be checked separately. FINAL and official tests are separate."
exit "$result"
