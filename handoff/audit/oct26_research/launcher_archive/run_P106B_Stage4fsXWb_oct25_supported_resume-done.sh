#!/usr/bin/env bash
# Same supported-source V3 resume within the delegated25Oct window only.
# Original source, sampler, MTP, thinking and cursor stay unchanged.
# A fresh STOP path preserves previous markers. No student or quality admission.
# Owned supervisor includes120s STOP/cleanup; at most7200s plus30s OS teardown.
# Absolute production stop12:40KST, full stdout retained in producer.log.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
deadline=2026-10-25T03:40:00+00:00
source_pin=CBA05428319BD533A087C8E0217824BAE4F9A822DABB3014BD497BA925B01CBC
tag=p106b_supported_supervisor_v1_20261025_oct25a
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_supported_supervisor.py --check-only
fi
window_seconds="$("$python_bin" -B -X utf8 -c 'from datetime import datetime,timezone; end=datetime.fromisoformat("2026-10-25T03:40:00+00:00"); seconds=min(7200,int((end-datetime.now(timezone.utc)).total_seconds())-120); assert seconds>=300,"not enough delegated production/cleanup time remains"; print(seconds)')" || exit $?
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
stop_file="HF/sft_ready/p106b_supported_production8h_v3_s1337/STOP_CODEX_SUPERVISOR_${tag}"
"$python_bin" -B -X utf8 -c 'from scripts.interactive_research_infer import require_idle_gpu; require_idle_gpu()' || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsXWb_oct25_supported_resume_"$stamp" --note "Explicit existing-V3 resume with owned supervisor, maxwall=$window_seconds, absolute deadline=$deadline, fresh stop_file=$stop_file. Parent prep/STOP/cleanup all included with120s reserve. Old batches and STOP stay immutable. MTP ON nmax2, context8192 thinking1024 output3072 and sampler unchanged. Full stdout is retained at test_result/evidence/$tag/producer.log. Technical candidates are unverified; no student, TRAIN_READY or75M completion."
timeout --signal=TERM --kill-after=30s "${window_seconds}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsXWb_oct25_supported_resume_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_supervisor.py --execute --tag "$tag" --source-sha256 "$source_pin" --max-wall-sec "$window_seconds" --deadline-utc "$deadline"
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsXWb_oct25_supported_resume_"$stamp" --note "Actual root exit=$result. Require matching supervisor receipt/terminal, actual producer exit, full raw/candidate references, exact predecessor/cursor/quota/shards and owned cleanup. Controlled pause8 is not model failure or content PASS; forced cleanup/errors are9. Supervisor SIGKILL cannot guarantee all descendants; root must verify actual owned PIDs and GPU quiescence. Never truncate partial batches or reset retries."
exit "$result"
