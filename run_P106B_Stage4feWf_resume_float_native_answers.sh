#!/usr/bin/env bash
# P106B_Stage4feWf_resume_float_native_answers: own resume namespace; original parents/source/dates stay read-only.
# User authority ends20261021T08Z; training stop05Z; no native pretraining rerun.
# CPU prepare is not model quality. No stdin/download/old overwrite or generic float loader.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4feWf_resume_float_native_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4feWf_resume_float_native_answers_"$run_stamp" --num 101 --note 'Explicit frozen-source resume family. Original native CPs and ternary SFTcost are validated under their original provenance. Same SFT384/body/optimizer/masks; new output/date metadata only. Single GPU, CPU preflight before actual, five-minute idle before cost. Worker cap1800s, no old mutation or automatic quality verdict. Native/SFT first answers separate; each public file below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4feWf_resume_float_native_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_resume.py --mode evaluate --arm float --endpoint native --max-wall-sec 1800 --execute
