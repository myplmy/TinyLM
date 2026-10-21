#!/usr/bin/env bash
# Six immutable CPs x24 fixed probes x4 prompt packages. Inference only.
# Own600-second worker; no training, checkpoint writes, teacher, best-of or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] Immutable stage accepts no positional arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4frWa_prompt_access_six_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4frWa_prompt_access_six_"$run_stamp" --num 101 --note 'Independent nontraining study:6fixedCP,24questions/12roots,4prompt packages,576firstanswers,384literal/192qualitative, FP32MATH/TF32off/KVon/MTPoff/greedy64/context1024. Primary exact raw, secondary strip-only; general answers human review. Fixed96 actual samples/24progress plus full raw. No blind/general-IQ or best-of claim. Own600worker, evaluate16:40/report17KST21st, old trace12KST HOLD unchanged; no teacher/training/checkpoint writes/download/old overwrite. Verify model body/source before and after. Structural finish not semantic truth; partial preserved, no rerun. evaluate only; model loads 6; all public files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4frWa_prompt_access_six_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_prompt_access.py --mode evaluate --max-wall-sec 600 --execute
