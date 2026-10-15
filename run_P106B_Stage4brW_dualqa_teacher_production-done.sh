#!/usr/bin/env bash
# Completed1920 sources/3840QA, raw000516 exit0; source/code lineage preserved.
# Teacher generation is sealed32-context batches; processed roots never restart.
# Q1-repeat control intentional duplicates allowed; no online semantic word list.
# No protected data/download/old writes/student training; deadline Oct16 17:00 KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4brW_dualqa_teacher_production_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4brW_dualqa_teacher_production_"$run_stamp" --num 101 --note 'Teacher source corpus only, not75M completion or student quality. Source bytes/code/seed/attempts preserved; same parent later for repeat-Q1 vs distinct-Q2 two-turn education. Fresh test content hidden until evaluation. Soft budget pause8 is not a scientific quality failure; original sources/checkpoints immutable. Full source provenance and20MB shards retained.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4brW_dualqa_teacher_production_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_production.py --mode generate --execute --max-wall-sec 14400
