#!/usr/bin/env bash
# Completed 2026-10-16 15:21:46 KST; raw152101 exit0,192 first answers and96 anchors.
# Same-fact question wording control; not new training or a memory feature.
# CPU seconds or bounded600 GPU seconds, one model at a time.
# Only this stage's prerequisites fail closed. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dfW_evidence_style_actual_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a fresh stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dfW_evidence_style_actual_"$run_stamp" --num 101 --note 'Same3 checkpoints,32 conditions by2 question wordings,192 first answers. Prior actual/recount must finish. Style3 exact96 replay, no training/teacher/CPT. Posthoc development only, not semantic quality PASS. Raw/weights private below20MB shards. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dfW_evidence_style_actual_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_style.py --mode evaluate --max-wall-sec 600 --execute
