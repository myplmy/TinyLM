#!/usr/bin/env bash
# Same32 frozen sources, controlled versus natural prompts on parent and three endpoints.
# No training/checkpoint save. Approx0.10h; FP32 math, cacheON, MTPoff, first answers only.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4yW_source_prompt_pair_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4yW_source_prompt_pair_"$stamp" --num 101 --note 'Common source32 x two prompt formats x four endpoints. First answers, no retry/train/weight save. Read literal agreement separately from semantics. Source raw local only; no independent world-test claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4yW_source_prompt_pair_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_prompt_pair.py --execute --max-wall-sec 600
