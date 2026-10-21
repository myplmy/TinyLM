#!/usr/bin/env bash
# P078 V2: fresh official-TRAIN holdout groups, original body TRAIN and four-arm cost unchanged.
# Fixed seed1337 and128 rows per language/split; no teacher or official evaluation gold.
# Root-pinned V3 corpus and V2 holdout SHA plus current authorization required.
# CPU source prepare is separate; measured cost8/full pending budget precede head fitting.
# Real stage or nonzero HOLD; no stdin wait, automatic adoption or old-gate repair.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage3Wb_prefix_router_v2_"${stamp}"_"$$" --num 066 --note 'V2 fresh official-TRAIN groups, no original TRAIN or four-arm cost changes. V1 split shortage remains HOLD. Require source/schema/byte pins, no model-based selection, cost8 and all-pending40h/current UTC budget. No fully-blind pretraining claim. Actual answers and raw counts, not CE alone, govern interpretation.'
exec "${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage3Wb_prefix_router_v2_"${stamp}"_"$$" --num 066 -- "${python_bin}" -B -X utf8 scripts/diag_p078_prefix_router.py "$@"
