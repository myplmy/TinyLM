#!/usr/bin/env bash
# CPU archived-native AST, exact source migrations and same-prefix fixtures
# No stdin, download, old mutation or unverified default precision switch.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage8aW_cache_precision_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve original raw; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage8aW_cache_precision_cpu_"$run_stamp" --num 103 --note 'CPU archived-native AST, exact source migrations and same-prefix fixtures. Technical output matching is not correct-answer or repetition repair PASS. GPT execution allowed only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage8aW_cache_precision_cpu_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p093b_generation_probe scripts.test_p101a_mtp_parity
