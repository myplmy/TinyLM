#!/usr/bin/env bash
# Recovery of Wa: original sandbox NVML blocked before teacher/model; raw kept.
# V2 adds actual8h wall connection, successful-pilot shard verification and UTC recheck.
# Four groups max600sec. Technical completion is not semantic quality.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_supported_production8h
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWab_supported_teacher_pilot_recovery_"$stamp" --num 101 --note 'V1 failure preserved: sandbox NVML blocked before model. New V2 source and destination, actual8h clock/pilot shard success/UTC recheck covered by regression. Same MTP/sampling/thinking,4groups cap; technical pause8 is not negative student quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWab_supported_teacher_pilot_recovery_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode pilot --max-wall-sec 600 --execute
