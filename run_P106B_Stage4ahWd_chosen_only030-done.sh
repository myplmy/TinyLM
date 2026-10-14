#!/usr/bin/env bash
# Same SFT/native/pair compute, chosen-only extra NLL0.3 control. About0.25h GPU.
# Separates pair contrast from extra positive reinforcement; no rejection gradient.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWd_chosen_only030_"$stamp" --note 'Chosen-only extra NLL0.3 control. Same pairs/native/SFT and forward computation; rejected answers have no objective gradient. Compare with ORPO-style0.3 as a whole-objective contrast, not exact gradient-strength matching.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWd_chosen_only030_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode train --arm positive030 --execute --max-wall-sec 3600
