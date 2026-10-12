#!/usr/bin/env bash
# Bounded production-question MTP pair, not another simple role benchmark.
# Historical off is preserved; new paired off/on keep source/question/history.
# Max GPU phase540s plus cleanup; no student/training/checkpoint or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
name=P106B_Stage6eWa_mtp_production_quality
log="test_result/101_log_$(date +%Y%m%d)_${name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWa_mtp_production_quality --num 101 --note 'Six frozen production questions: KO/EN x QA/JSON/final multi-turn. Old OFF replies plus matched fresh OFF/ON. Technical completion is not quality. Whole bounded GPU phase540s; no student or training; no automatic production change.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWa_mtp_production_quality --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_gemma_mtp_production.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWa_mtp_production_quality --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_mtp_production.py --tag p106b_gemma_mtp_production_quick_v1_s1337 --rounds 1 --max-wall-sec 540 --execute
