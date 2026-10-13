#!/usr/bin/env bash
# Same course and parent, NTP low1e-5 joint LR; code-controlled task and native retention
# Separate small quality experiment; unchanged75M x4epoch goal.
# No stdin, download, old mutation or protected data.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4qWb_context_ntplo_repeat4_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw log; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4qWb_context_ntplo_repeat4_"$run_stamp" --num 101 --note 'Same course and parent, NTP low1e-5 joint LR; code-controlled task and native retention. Eight procedural types are not general world intelligence. Check actual answers, masks, tokens, nativeCE and cost separately. GPT execution authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4qWb_context_ntplo_repeat4_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_context_quality.py --mode train --arm ntp_lo --execute --max-wall-sec 1800
