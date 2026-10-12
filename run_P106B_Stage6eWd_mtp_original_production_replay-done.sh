#!/usr/bin/env bash
# WhyWd: fixed-question recovery tests added a new echo constraint, not production.
# Replay original successful OFF production payloads verbatim with MTP ON; old
# OFF source/data is preserved. Compare source/question/answer after generation.
# Max180s; total authorized direct GPU phases stays below10min; no student.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6eWd_mtp_original_production_replay.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWd_mtp_original_production_replay --num 101 --note 'Original production payloads verbatim, no new fixed-question echo constraint. Six KO/EN QA/JSON/final-multiturn ON replies vs immutable historical OFF source/data; historical speed remains descriptive. Max180s; no student/training/automatic production change.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWd_mtp_original_production_replay --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_gemma_mtp_production.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWd_mtp_original_production_replay --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_mtp_production.py --tag p106b_gemma_mtp_original_replay_v3_s1337 --rounds 1 --protocol production --on-only --max-wall-sec 180 --execute
