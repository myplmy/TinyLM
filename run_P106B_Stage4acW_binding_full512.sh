#!/usr/bin/env bash
# Entire frozen512 code-known validation, exact first-value heuristic and root-four consistency.
# Read-only saved student; no training/save. Approx0.05h/cap600s; same precision/cache/nativeK1.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4acW_binding_full512_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4acW_binding_full512_"$stamp" --num 101 --note 'Full512 same frozen validation. Newstudent exact answers and first-value code heuristic are separate; no random null, world intelligence or all-corpus claim. Root four-view consistency reported. No training/teacher/checkpoint save.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4acW_binding_full512_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_fullval.py --execute --max-wall-sec 600
