#!/usr/bin/env bash
# Dev-only paired targeted continuous versus latent-requantized edits.
# Estimate: 10 to 60 minutes. No test selection, no optimizer, no CP save.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
PY="$(tinylm_python)"
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage2W_weight_direction_search --note "Dev selection only; original, effective and latent edits. Loop reduction alone is not answer-quality improvement; original rollback required."
"${PY}" -B -X utf8 scripts/runlog.py --num 108 --name P108_Stage2W_weight_direction_search -- timeout --signal=TERM --kill-after=20s 5000s "${PY}" -B -X utf8 -m scripts.diag_p108_weight_space search p108w_v1_20261104 new595-broad-q
