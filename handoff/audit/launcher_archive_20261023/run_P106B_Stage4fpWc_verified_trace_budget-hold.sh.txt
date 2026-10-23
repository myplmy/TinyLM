#!/usr/bin/env bash
# Isolated verified direct/short-trace pilot; frozen root/spec and own bounded authority.
# Failure/partial/HOLD is preserved; no auto restart, input prompt or old source mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] Immutable stage accepts no positional arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fpWc_verified_trace_budget_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw is preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fpWc_verified_trace_budget_"$run_stamp" --num 101 --note 'Verified short trace pilot: same actual newF704 initializer,4096 canonical roots/four passes128 updates/micro8 accum16/ckptON/BF16/default compile; common SFT pad128/native1024. Direct versus trace target masses79520/512464 and native1048576 each: not reasoning-only or token-efficiency causality. Own prepare12KST/train14KST/end17KST on20261021; active10800, both cost8/all-pending train/eval/record budget mandatory. TEST1024+TRAIN32+USER6 per endpoint, raw IDs/strict final and trace separate. No stdin/download/teacher/new heads/MTP/old overwrite; closed readonly recount required, not quality adoption; public files below20MB. Modebudget cap600s.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fpWc_verified_trace_budget_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_verified_trace.py --mode budget --max-wall-sec 600 --execute
