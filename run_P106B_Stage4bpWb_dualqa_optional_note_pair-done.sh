#!/usr/bin/env bash
# v2 fixes optional empty metadata; never strips leading reasoning or relaxes QA.
# Same8 source and v1 root/attempt seeds, same Gemma MTP/thinking/sampler/budgets.
# Saved reparse is not new GPU evidence; actual v2 comparison has separate output.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bpWb_dualqa_optional_note_pair_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve previous raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bpWb_dualqa_optional_note_pair_"$run_stamp" --num 101 --note 'Mandatory Q/A only, optional empty NOTE filled by code. Preface/reasoning and missing required answers still rejected. Shared3 attempts and typed insufficiency protection retained. Original v1 response/verdict immutable. Reparse and fresh GPU evidence must not be merged; source-relative truth remains unverified.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bpWb_dualqa_optional_note_pair_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_optional_note.py --mode pilot --execute --max-wall-sec 3600
