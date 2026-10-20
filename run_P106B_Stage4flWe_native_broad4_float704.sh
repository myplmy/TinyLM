#!/usr/bin/env bash
# P106B_Stage4flWe_native_broad4_float704: exact C2 native-parent Broad4 experiment; no new source/weights/semantics.
# Train caps from closed paired cost and measured budget; continuous optimizer across two cycles.
# Original raw/CP stay immutable. Child PASS is not answer quality; no stdin or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This immutable stage accepts no arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4flWe_native_broad4_float704_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4flWe_native_broad4_float704_"$run_stamp" --num 101 --note 'C2 original22528 records/native QF parents. Same micro8 accum16/seq1024/checkpoint-on/L0/Muon/clip1/default compile. Four passes704 and5632 native windows; optimizer retained across cycles. Closed Q/F cost and fresh current-time budget required; active14400/eval1200/record600 and21st14KST training/17KST authority unchanged. Mode train, worker cap2400s; after actual train closed-worker readonly VERIFY is mandatory. Actual1694 first answers and source16/max17 dialogue answers are separate from general3turn ability. Files below20MB; no quality auto-adoption.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4flWe_native_broad4_float704_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_broad4_recovery.py --mode train --arm float --max-wall-sec 2400 --execute
