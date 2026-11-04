#!/usr/bin/env bash
# V2 winner fixed before heldout; original plus three norm-matched controls.
# Estimate 10 to 60 minutes; all raw answers preserved in sub-3MB shards.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
PY="$(tinylm_python)"
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage3bW_weight_direction_confirm --note "V2 heldout plus ordinary dialogue. These practice results are not an official benchmark or full-training intelligence improvement."
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage3bW_weight_direction_confirm -- timeout --signal=TERM --kill-after=20s 5000s "${PY}" -B -X utf8 -m scripts.diag_p108_weight_space confirm p108w_v2_20261104 new595-broad-q
