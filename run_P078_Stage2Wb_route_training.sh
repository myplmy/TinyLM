#!/usr/bin/env bash
# P078 Stage2: independent real eager route-SFT controller, MTP off.
# Supply mode/arm, exact frozen-corpus SHA and separately approved authority.
# Four cost32 runs precede fresh all-pending budget and four-pass training.
# No implied GPU grant; READY false or missing inputs is HOLD/nonzero.
# Actual wall/VRAM is unmeasured until cost32; family forecast must fit40h.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage2Wb_route_training_"${stamp}" --num 066 --note 'Separate explicit authorization/corpus SHA required. Four actual cost32 receipts precede fresh family40h budget; four-pass count derived from frozen manifest. MTP off, eager common shape, primary matched training policy, common-uniform is mismatch secondary only. No learned-router or quality claim from check-only/toy.'
exec "${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage2Wb_route_training_"${stamp}" --num 066 -- "${python_bin}" -B -X utf8 scripts/diag_p078_route_training.py "$@"
