#!/usr/bin/env bash
# Four independent scratch/parent x NTP/MTP arms on NEW explicit-context course.
# Each cost32 precedes its four-pass704update train; max4h/arm, no stdin.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
failed=0
for arm in scratch_ntp scratch_mtp parent_ntp parent_mtp; do
    "$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3jW_"$arm"_"$stamp" --num 092 --note 'New22528TRAIN/512DEV corpus; actual5.405M x/pass,552609targets/pass,4passes704updates, m8a16/ckptON/seq1024, LR5e-5/Muon2e-4, correction-turn masks. Official TRAIN annotations used; official evaluation gold not trained. Not old8M rerun or75M completion. Cost32 is resource only; same-code cost required. Independent arms continue after failure.'
    cost_rc=0
    "$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3jW_"$arm"_"$stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/check_p101a_clean_cost.py --family mtp --arm "$arm" --check-only || cost_rc=$?
    if [[ "$cost_rc" == 8 ]]; then
        "$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3jW_"$arm"_"$stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_clean_bilingual.py --family mtp --mode calibrate --arm "$arm" --max-wall-sec 1200 --execute || cost_rc=9
        [[ "$cost_rc" == 8 ]] && cost_rc=0
    fi
    if [[ "$cost_rc" != 0 ]]; then
        failed=1
        continue
    fi
    if ! "$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3jW_"$arm"_"$stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_clean_bilingual.py --family mtp --mode train --arm "$arm" --max-wall-sec 14400 --execute; then
        failed=1
        continue
    fi
    if ! "$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3jW_"$arm"_"$stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_clean_eval.py --family mtp --arm "$arm" --max-wall-sec 1800 --execute; then
        failed=1
    fi
done
exit "$failed"
