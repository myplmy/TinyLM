#!/usr/bin/env bash
# Read-only four endpoints same old24 development prompts; no training or new checkpoint; not independent
# Estimated .08h; no stdin/download/cleanup; independent raw timestamp.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4xWb_format_mix_dev24_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4xWb_format_mix_dev24_"$stamp" --num 101 --note 'Read-only four endpoints same old24 development prompts; no training or new checkpoint; not independent. Read execution, actual token counts, raw answers and final verdict separately. Literal agreement is not semantic truth. Keep third party source raw local.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4xWb_format_mix_dev24_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_format_mix.py --mode dev --execute --max-wall-sec 600
