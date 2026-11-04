#!/usr/bin/env bash
# Frozen winner, original and three norm-matched random controls on heldout.
# Estimate: 10 to 60 minutes; independent practice is not an official benchmark.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
PY="$(tinylm_python)"
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage3W_weight_direction_confirm --note "Frozen winner and three random controls; preserve all question-answer pairs; correctness, copies, requested repeats and empty outputs are separate."
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage3W_weight_direction_confirm -- timeout --signal=TERM --kill-after=20s 5000s "${PY}" -B -X utf8 -m scripts.diag_p108_weight_space confirm p108w_v1_20261104 new595-broad-q
