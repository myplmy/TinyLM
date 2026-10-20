#!/usr/bin/env bash
# P106B_Stage4fmWc_native595_budget: explicit4543 native recipe; old controller and defaults never rebound.
# Same scratch028C46, expanded1191116192 pool/externalVAL3005000; no teacher/MTP/headwise.
# CPU/source, measured cost and budget are prerequisites; no stdin/download/old overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This immutable stage accepts no arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fmWc_native595_budget_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWc_native595_budget_"$run_stamp" --num 101 --note 'Native595 conditional study:4543x8x16x1024 main targets595460096, pool1191116192/externalVAL3005000/scratch028C46. Native Adam/Muon/WSD/anneal/clip1 retained. Cost8 main1048576 plus separate late8192 backward-only/cache checks; no cost CP or quality claim. Actual-worker43200, train cap18000, native stop21st11:30KST/global train14KST/authority17KST. Followup7200/eval1200/record600 reserved; new measured paired budget and fresh300s full-code-map proof before cost. Stage budget cap600s. All public files below20MB; old source/CP/raw unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWc_native595_budget_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595.py --mode budget --max-wall-sec 600 --execute

