#!/usr/bin/env bash
# P106B_Stage4fkW0_expansion_val_overlap_cpu: independent readonly validation of retained TRAIN.
# Same EOS/edge rule and separate32 full native probe windows. No model/GPU/training.
# CPU cap600s plus record reserve600s; no new source mutation or semantic quality approval.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This launcher takes no arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fkW0_expansion_val_overlap_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fkW0_expansion_val_overlap_cpu_"$run_stamp" --num 101 --note 'CPU-only independent readonly scan of exact retained1191116192 TRAIN IDs and external3005000 VAL IDs. Same full-EOS/edge patterns plus separate32x1025 exact windows, uint16 alignment, all-byte SHA/count/EOS. No original source/cache changes, model/CP/GPU, automatic training admission or semantic decontamination claim. Regression, metadata preflight, complete scan then closed-activity verification. Worker cap600s and record reserve600s; authority ends20261021T08Z. Files below20MB; actual hits are recorded separately from scan failure.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fkW0_expansion_val_overlap_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_expansion_val_audit.py --execute --max-wall-sec 600
