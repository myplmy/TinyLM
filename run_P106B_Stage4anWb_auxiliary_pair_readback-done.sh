#!/usr/bin/env bash
# Completed2026-10-15 raw110232 exit0; see exact result scope, no global quality promotion.
# CPU only after all5 actual test reports; declared code view pairs and root-bootstrap, no model.
# Read-only inputs and fresh small report; no stdin/implicit resume/downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4anWb_auxiliary_pair_readback_"$stamp" --note 'CPU only after all5 actual test reports; declared code view pairs and root-bootstrap, no model.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4anWb_auxiliary_pair_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/summarize_p106b_learning_pair.py --tag p106b_binding_aux_v1_s1337 --execute
