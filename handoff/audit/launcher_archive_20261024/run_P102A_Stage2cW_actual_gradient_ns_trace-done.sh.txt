#!/usr/bin/env bash
# New Stage2cW: actual parent gradients, not the old synthetic2x2 sensitivity probe.
# Same frozen first128, FP32 MATH, micro8/accum16, original clipping and Muon.
# No checkpoints, adoption, quality claim, installation or interactive input.
# One-time delegated window ends24Oct09KST; internal stop08:40, hard cap1200s.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p102a_head_muon_trace.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2cW_actual_gradient_ns_trace_"$stamp" --note 'Actual raw157/clipped157/NS85 replay; reference and streaming each1update. Original tolerances retained. Instrumented time is not speedup; knownV3 is numerical-only, not admitted. Exit8 is a valid numerical negative, not adoption. Source and assets must remain unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2cW_actual_gradient_ns_trace_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p102a_head_muon_trace.py --execute --source-sha256 6F67881E57C933261D3ECB716AACA29528FD7BB5C0A3366576BD4733C5592F6E --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec 1200
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2cW_actual_gradient_ns_trace_"$stamp" --note "Final exit=$result; report and matrix controls determine validity. No product optimizer/head setting is changed. The actual trace and independent numerical conclusions are separate from intelligence and full-training readiness."
exit "$result"
