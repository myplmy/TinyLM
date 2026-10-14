#!/usr/bin/env bash
# Freeze8192/1024 broad-fiction course, real student tokens; original source untouched
# No stdin/download/old mutation; not75M world knowledge or default adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4t1W_broad_context_corpus_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4t1W_broad_context_corpus_"$run_stamp" --num 101 --note 'Freeze8192/1024 broad-fiction course, real student tokens; original source untouched. Values/wording/volume differ from old4q; no single-axis causal claim across corpora. Separate actual answers/unknown free review/nativeCE/padding. GPT run only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4t1W_broad_context_corpus_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_context_broad.py --mode corpus --execute --max-wall-sec 300
