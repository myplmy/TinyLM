#!/usr/bin/env bash
# Completed new supported512/64 required; same code5120, source QA replacement and fresh final640.
# Completed2026-10-15 raw095115 exit0; same5632/704 and new640 test frozen.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wb_binding_aux_corpus_"$stamp" --note 'Completed new supported512/64 required; same code5120, source QA replacement and fresh final640.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wb_binding_aux_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode freeze --decision-note 'Frozen-feature factor probes suggest weak target connection; new source block shared by all arms, not old recipe causal comparison' --execute
