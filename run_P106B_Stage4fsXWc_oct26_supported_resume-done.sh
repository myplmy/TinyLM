#!/usr/bin/env bash
# Authorized26Oct2026 autonomous window, same V3 teacher-only incremental run.
# At most8h, ending before17KST. No source/sampling/pilot/student changes.
# Exit8 preserves a bounded production pause; it is not a quality verdict.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
deadline_utc="2026-10-26T08:00:00Z"
task_seconds=$(( $(date -u -d "$deadline_utc" +%s) - $(date -u +%s) - 120 ))
[[ "$task_seconds" -ge 60 ]] || exit 8
[[ "$task_seconds" -le 28800 ]] || task_seconds=28800
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode resume --max-wall-sec "$task_seconds" --deadline-utc "$deadline_utc" --check-only
fi
"$python_bin" -B -X utf8 -c 'from scripts.interactive_research_infer import require_idle_gpu; require_idle_gpu()'
result=$?
[[ "$result" == 0 ]] || exit "$result"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
stop_file="HF/sft_ready/p106b_supported_production8h_v3_s1337/STOP_OCT26_${stamp}"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsXWc_oct26_supported_resume --note "Authorized sameV3 resume: max_seconds=$task_seconds deadline=$deadline_utc stop_file=$stop_file. Existing batches and STOP markers stay unchanged. Exit8 is a bounded pause, not a semantic PASS or student training."
exec timeout --signal=TERM --kill-after=60s "${task_seconds}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4fsXWc_oct26_supported_resume -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode resume --max-wall-sec "$task_seconds" --deadline-utc "$deadline_utc" --stop-file "$stop_file" --execute
