#!/usr/bin/env bash
# HOLD: V1 old VAL512 split shortage; original wrapper source1e63c6d.
# P078 Stage3 learned prefix-router pilot; original Stage2 and old negative gates stay intact.
# Separate root authorization and actual V3 balanced704 body are prerequisites.
# Cost8 and all-pending 40h/current UTC budget must close before labels/fit/test.
# FP32 MATH, cache OFF, body frozen, MTP OFF; head micro8 accum16, body checkpoint ON.
# This launcher runs a real selected stage or fails HOLD; it never waits on stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage3Wa_prefix_router_"${stamp}"_"$$" --num 066 --note 'Independent learned prefix router. Read actual raw and closed receipts, not static status. No automatic adoption. Body VAL was already used: router TEST only is unseen by the router. Resource-only R1 cost is not label-quality evidence. All stages fail closed on missing balanced704, source, deadline, cost or full pending budget.'
exec "${python_bin}" -B -X utf8 scripts/runlog.py --name P078_Stage3Wa_prefix_router_"${stamp}"_"$$" --num 066 -- "${python_bin}" -B -X utf8 scripts/diag_p078_prefix_router.py "$@"
