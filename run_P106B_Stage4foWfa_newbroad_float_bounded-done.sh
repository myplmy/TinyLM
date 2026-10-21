#!/usr/bin/env bash
# Same final endpoint, stricter420-second worker under unchanged original3600 family.
# Original failed900-cap admission is preserved; all regression/preflight still run.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] Immutable stage accepts no positional arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4foWfa_newbroad_float_bounded_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw is preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4foWfa_newbroad_float_bounded_"$run_stamp" --num 101 --note 'Original900 cap was not admitted and created no last worker/result. Same complete1920-request/1919-scored final endpoint now explicitly caps420seconds; original3600 family, regression67, preflight600 and21st17KST unchanged. Prior closed five are not rerun. Readonly separate CPU audit is not an original-family readback completion. No stdin/download/new Falcon/training/checkpoint/old overwrite. Resource HOLD is not model failure; data/generation/score conditions unchanged, no completion guarantee. Public files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4foWfa_newbroad_float_bounded_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595_public.py --mode evaluate --model-id newbroad_float --max-wall-sec 420 --execute
