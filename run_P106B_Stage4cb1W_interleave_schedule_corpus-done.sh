#!/usr/bin/env bash
# New interleaved relation schedule; no old data/CODE/CPT overwrite or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cb1W_interleave_schedule_corpus_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb1W_interleave_schedule_corpus_"$run_stamp" --num 101 --note 'Same existing22.070M SFT information, source-pointer schedule only. New test roots and source32, later-role TEST reserved unseen. Not75M/300M or world intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb1W_interleave_schedule_corpus_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_course.py --execute
