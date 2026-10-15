#!/usr/bin/env bash
# Completed2026-10-15 raw102534 exit0;176 actual control updates, final test pending.
# Negative-control auxiliary labels root-flipped at coefficient1.0. SFT answers unchanged, not deployment candidate.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWd_binding_aux_permuted100_"$stamp" --note 'Negative-control auxiliary labels root-flipped at coefficient1.0. SFT answers unchanged, not deployment candidate.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWd_binding_aux_permuted100_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode train --arm auxperm100 --execute --max-wall-sec 3600
