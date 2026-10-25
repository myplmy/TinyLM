#!/usr/bin/env bash
# DONE: actual full19965/67106 closed, root audit and commands in result101 section492.
# GPT2-only full evaluation. Frozen numerical policy and original receipts stay unchanged.
# Root must capture/monitor the separate-session worker PID before its deadline.
# Parent timeout10675+kill5 leaves120sec of the whole10800sec for owned cleanup.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_window.py --check-only
fi
if [[ "${TL_ROOT_NATIVE_PID_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root live PID capture, deadline supervision and owned cleanup are required.'
  exit 8
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pWb_gpt2_verified_window10800_"$stamp" --note 'Strict native42713 and window5BA4870D. Official full19965rows67106choices, exact original canary/cost/HOLD receipts. Independent whole10800sec plus24Oct08:40KST. Parent hardcap10675INT+5KILL, root-owned worker PID supervision and120sec cleanup reserve required; acknowledgement is not evidence. No training/install.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pWb_gpt2_verified_window10800_"$stamp" -- /usr/bin/timeout --signal=INT --kill-after=5s 10675s "$python_bin" -B -X utf8 scripts/p106b_native_window.py --execute --model gpt2_q4km --mode full --source-sha256 5BA4870D37800DE70A004305D644DD4263F9785B763B299647F1316DDE29A525 --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec 10800
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pWb_gpt2_verified_window10800_"$stamp" --note "Process exit=$result. Require matching terminal_receipt+report SHA, no failure veto, full19965/67106 raw recount, actual parent exit0 and verified owned-worker exit/GPU idle within budget. Timeout124/137 is not a score. Root closure audit remains required."
exit "$result"
