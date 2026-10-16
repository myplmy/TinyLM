#!/usr/bin/env bash
# Attempt complete; result/raw/code identity preserved, not an automatic quality PASS.
# Freeze all TEST, cube, retention and existing public inputs before child answers; CPU only.
# Estimated .04h; independent cost/test contracts are not intelligence claims.
# One-time authority ends2026-10-17 10:00KST; no new GPU after09:00.
# No stdin, model writes, old mutations, downloads or online semantic filtering.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dm0W_night_eval_frozen_inputs_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dm0W_night_eval_frozen_inputs_"$run_stamp" --num 101 --note 'Freeze all TEST, cube, retention and existing public inputs before child answers; CPU only. Read semantic limits, exact complete denominators, source/prompt/raw SHA and paired intervals. MC likelihood and stopping are not free-answer understanding; source annotation is not full truth adjudication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dm0W_night_eval_frozen_inputs_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_evaluation scripts.test_p106b_night_eval
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dm0W_night_eval_frozen_inputs_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_eval.py --mode freeze --max-wall-sec 7200 --execute
