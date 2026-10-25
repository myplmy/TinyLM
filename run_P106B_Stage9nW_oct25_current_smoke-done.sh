#!/usr/bin/env bash
# Current-source canonical smoke in the delegated25Oct13KST window.
# Same canonical module and checks; existing isolated output adapter only.
# Expected7-10min;1200sec cap is not a forecast or quality guarantee.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/codex_smoke.py --mode check --session-id oct25_cab_v1
fi
"$python_bin" -B -X utf8 -c 'from datetime import datetime,timezone; d=datetime.fromisoformat("2026-10-25T04:00:00+00:00"); remaining=(d-datetime.now(timezone.utc)).total_seconds(); assert remaining>=1230,"full smoke reservation does not fit delegated deadline"' || exit $?
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9nW_oct25_current_smoke_"$stamp" --note 'Current canonical smoke. Original settings and checks; isolated outputs. Limit1200sec and25Oct13KST, independent OS timeout. No external scores, original checkpoint overwrite or package changes.'
timeout --signal=TERM --kill-after=15s 1230s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9nW_oct25_current_smoke_"$stamp" -- "$python_bin" -B -X utf8 scripts/codex_smoke.py --mode full --session-id oct25_cab_v1 --execute --deadline-utc 2026-10-25T04:00:00Z --max-wall-sec 1200
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9nW_oct25_current_smoke_"$stamp" --note "Final exit=$result. Verify actions, owned child exits, final summary, source/assets unchanged and cleanup. This does not establish fused CE, v12, full IQ2 scores or intelligence improvement."
exit "$result"
