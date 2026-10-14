#!/usr/bin/env bash
# CPU real driver import and four-argument prompt-budget API, exact references and shared retries
# No stdin/download/old mutation; semantic review after generation only.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4s0Wb_visible_source_budget_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4s0Wb_visible_source_budget_cpu_"$run_stamp" --num 101 --note 'CPU real driver import and four-argument prompt-budget API, exact references and shared retries. Header/reference/budget checks are structural, not quality PASS; exact questions/answers shown. GPT runtime only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4s0Wb_visible_source_budget_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_visible_source scripts.test_p106b_gemma_ac
