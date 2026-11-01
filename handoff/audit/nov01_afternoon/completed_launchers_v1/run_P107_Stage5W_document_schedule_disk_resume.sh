#!/usr/bin/env bash
# Technical six-update replay, explicit synthetic documents and full sharded disk state.
# CPU15 and fresh pinned profile required; serialize only to new runs/isolated path.
# No corpus/quality claim, no parent mutation or deletion. Single GPU after Falcon full.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--profile handoff/audit/nov01_afternoon/P107_DISK_PROFILE_v1.json --profile-sha256 8BDA8C4334925C178B83856F3DC02A3002888F13E193FAA8B0329F2E79DB8ECD --mode resume --max-wall-sec 900)
"$python_bin" -B -X utf8 scripts/diag_p107_disk_resume.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 1020s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage5W_document_schedule_disk_resume -- "$python_bin" -B -X utf8 scripts/diag_p107_disk_resume.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage5W_document_schedule_disk_resume --note "actual_exit=$result; six synthetic optimizer updates, explicit-document sampler, same scheduled continued/resumed state must be exact. One new research-only disk snapshot in bounded16MB shards; no deletion, corpus, quality or power-loss claim. Deadline15:00 KST, final ownedCUDA0 and original parent/source unchanged."
exit "$result"
