#!/usr/bin/env bash
# CPU3 and supply inventory; exclude old736 roots/long messages. About0.08h CPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0W_source_expand_inventory_"$stamp" --note 'CPU3 then new source supply. Full source512 token reserve is a budget, not semantic rejection. Exclude old roots/long source identities; no GPU, protected dictionary or downloads.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0W_source_expand_inventory_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_source_expand.py
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj0W_source_expand_inventory_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_expand.py --mode inventory --execute
