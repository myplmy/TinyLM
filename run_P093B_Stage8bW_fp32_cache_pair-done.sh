#!/usr/bin/env bash
# Saved parent/shared/r64:96 cache x precision generations, no training/checkpoint writes
# No stdin, download, old mutation or unverified default precision switch.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage8bW_fp32_cache_pair_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve original raw; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage8bW_fp32_cache_pair_"$run_stamp" --num 103 --note 'Saved parent/shared/r64:96 cache x precision generations, no training/checkpoint writes. Technical output matching is not correct-answer or repetition repair PASS. GPT execution allowed only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage8bW_fp32_cache_pair_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_cache_precision.py --execute --max-wall-sec 600
