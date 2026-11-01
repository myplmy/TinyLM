#!/usr/bin/env bash
# Read the existing synthetic Stage5W disk snapshot in a fresh worker.
# Exactly two resumed updates; no new checkpoint, corpus or quality claim.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--profile handoff/audit/nov01_afternoon/P107_PROCESS_PROFILE_v1.json --profile-sha256 FFAA9801A830E918575379A4A11D34715FD6B468CCACD73F220A621613A30A3D --mode resume --max-wall-sec 300)
"$python_bin" -B -X utf8 scripts/diag_p107_process_resume.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 420s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage7W_fresh_process_disk_resume -- "$python_bin" -B -X utf8 scripts/diag_p107_process_resume.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage7W_fresh_process_disk_resume --note "actual_exit=$result; fresh process loads the existing Stage5W snapshot read-only, resumes exactly two updates and must reproduce full state/loss/targets/LR. Original None boundary retained under explicit archived-source compatibility evidence. No new checkpoint writes, corpus, quality or power-loss claim."
exit "$result"
