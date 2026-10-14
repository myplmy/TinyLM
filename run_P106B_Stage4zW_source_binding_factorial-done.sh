#!/usr/bin/env bash
# Same facts, target/order/value changes independently on four saved endpoints; no training/save. [Completed; command/SHA in WIP_20261014b_LOOKUP_LAUNCHER_ARCHIVE.]
# Code-known32 cases x four endpoints; FP32math/cacheON/nativeK1/greedy64. Approx0.1h/cap600s.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4zW_source_binding_factorial_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4zW_source_binding_factorial_"$stamp" --num 101 --note 'Code-known32 fictional lookup cases x parent/A/B/C. Same facts with target/order flips. No teacher/training/checkpoint save. First-value matching is descriptive, not proof of architectural cause or generic intelligence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4zW_source_binding_factorial_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_source_binding.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4zW_source_binding_factorial_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_binding.py --execute --max-wall-sec 600
