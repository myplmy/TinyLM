#!/usr/bin/env bash
# Completed2026-10-15 raw105644 CPU32; model0.
# CPU final contracts: fresh state generator, two-turn last mask, scoped callbacks and deadline math.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4av0Wf_state_final_cpu_"$stamp" --note 'CPU final contracts: fresh state generator, two-turn last mask, scoped callbacks and deadline math.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4av0Wf_state_final_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_state_update_aux scripts.test_p106b_state_update_driver scripts.test_p106b_binding_auxiliary scripts.test_p106b_binding_scale
