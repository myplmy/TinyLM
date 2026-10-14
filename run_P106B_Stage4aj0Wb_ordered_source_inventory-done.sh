#!/usr/bin/env bash
# v1 inventory only is preserved in7d7957d. Newv2 keeps original message/sentence order.
# CPU4 and supply inventory, about0.08h CPU; no model or source mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0Wb_ordered_source_inventory_"$stamp" --note 'Newv2 source inventory with original message/offset order for both teacher and student. Oldv1 CPU evidence is immutable. CPU4 then bounded supply census; no GPU/download/protected source.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0Wb_ordered_source_inventory_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_source_expand.py
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0Wb_ordered_source_inventory_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_expand.py --mode inventory --execute
