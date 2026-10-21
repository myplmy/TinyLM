#!/usr/bin/env bash
# DONE: actual CPU16 root launcher run20261021T221548; source07dc7e2.
# P078 Stage2: real tiny CPU route/backward/session regressions only.
# Estimated seconds, not a language-quality or real-parent/GPU measurement.
# Stop on any failed prerequisite; preserve all original data and checkpoints.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage2Wa_route_training_cpu_"${stamp}" --num 066 --note 'New P078 CPU toy contracts only. Original P078 closure/P070B numerical tolerance stay unchanged. Real corpus/checkpoint/GPU/router training are not run by this launcher.'
exec "${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage2Wa_route_training_cpu_"${stamp}" --num 066 -- "${python_bin}" -B -X utf8 scripts/diag_p078_route_training.py --mode toy --execute
