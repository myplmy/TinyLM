#!/usr/bin/env bash
# P106B_Stage4fiWd_headwise_muon_answers: one isolated Q/K head-wise NS-unit contrast, not full DeepSeek training.
# Same completed float-native parent and frozen SFT384; old Muon/data/CP/code stay unchanged.
# Actual-worker3600/record600; absolute21st17KST and training14KST. No stdin/download.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This launcher takes no arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fiWd_headwise_muon_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fiWd_headwise_muon_answers_"$run_stamp" --num 101 --note 'Same float native parent, unchanged L0/SFT4passes384/micro8 accum16/clip1/AMP/default compile/RMS/WD0. Q14/K-owner7 NS unit only. Cost8 requires matching UTC and monotonic300s root idle proof, end fresh600s; no continuous peak/OOM claim. No source retag or generic float loader. Execution worker closes activity before readonly strict VERIFY child and final three-phase verdict. Files below20MB. Worker cap900s; technical completion is not answer quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fiWd_headwise_muon_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_headwise_muon.py --mode evaluate --max-wall-sec 900 --execute
