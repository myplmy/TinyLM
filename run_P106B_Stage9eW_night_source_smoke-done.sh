#!/usr/bin/env bash
# Fresh full canonical smoke under the delegated24Oct09KST window.
# Same canonical actions, isolated outputs and bounded owned children; no parameter changes.
# This cannot replace the external HF numerical oracle or official benchmark.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/codex_smoke.py --mode check --session-id oct24_hf_v3
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9eW_night_source_smoke_"$stamp" --note 'Full canonical smoke on current source. Same user actions and checks, existing Codex isolated outputs only; no relaxation or external benchmark scores. Maximum1200sec and24Oct08:40KST. No install or original checkpoint overwrite.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9eW_night_source_smoke_"$stamp" -- "$python_bin" -B -X utf8 scripts/codex_smoke.py --mode full --session-id oct24_hf_v3 --execute --deadline-utc 2026-10-23T23:40:00Z --max-wall-sec 1200
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage9eW_night_source_smoke_"$stamp" --note "Final exit=$result. Verify smoke report COMPLETE, all child/actions, source/assets unchanged and cleanup. Static ERROR or actual HF/report errors remain independent."
exit "$result"
