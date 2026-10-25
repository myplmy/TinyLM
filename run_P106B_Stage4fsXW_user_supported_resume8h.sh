#!/usr/bin/env bash
# USER-OWNED NEXT WINDOW, not an extension of Codex authority after23Oct17KST.
# Explicit existing-V3 resume, at most8h plus60sec emergency teardown.
# Same MTP/pilot/source/sampling; no student, no quality/admission claim.
# Existing STOP markers and immutable batches stay untouched; no input wait.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode resume --max-wall-sec 28800 --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ "${TL_P106B_USER_8H:-}" != 1 ]]; then
  "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsXW_user_supported_resume8h_"$stamp" --num 101 --note 'HOLD: set TL_P106B_USER_8H=1 only for a separately chosen user-owned8h execution window. No model started; no interactive prompt. Review source-quality concerns first.'
  exit 8
fi
"$python_bin" -B -X utf8 -c 'from scripts.interactive_research_infer import require_idle_gpu; require_idle_gpu()'
result=$?
[[ "$result" == 0 ]] || exit "$result"
deadline="$(date -u -d '+8 hours' +%Y-%m-%dT%H:%M:%SZ)"
stop_file="HF/sft_ready/p106b_supported_production8h_v3_s1337/STOP_USER_${stamp}"
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsXW_user_supported_resume8h_"$stamp" --num 101 --note "USER-OWNED explicit sameV3 resume, deadline=$deadline stop_file=$stop_file. Preserve prior STOP/batches. Technical candidates remain unverified, not75M completion. Ctrl+C/TERM or the exact printed stop path closes an incremental batch; SIGKILL may leave a refused unfinished batch."
timeout --signal=TERM --kill-after=60s 28800s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsXW_user_supported_resume8h_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode resume --max-wall-sec 28800 --deadline-utc "$deadline" --stop-file "$stop_file" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsXW_user_supported_resume8h_"$stamp" --num 101 --note "Final exit=$result. Exit8 is a retained bounded production pause/HOLD, not a content PASS; inspect closed batch/report/manifests and memory gaps. Exit0 requires target report review; other exits remain failures. Do not restart an unfinished batch or reset retries."
exit "$result"
