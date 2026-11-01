#!/usr/bin/env bash
# Technical full-shape KL cost only. Same frozen native teacher, not better knowledge.
# New outputs, sixteen synthetic updates, no checkpoint writes or corpus training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--profile handoff/audit/nov01_afternoon/P107_KD_PROFILE_v1.json --profile-sha256 D365804AF972CC55686D321615B78D2B53E3260CF0751D209AC87BC728E2D25B --mode cost --max-wall-sec 900)
"$python_bin" -B -X utf8 scripts/diag_p107_causal_kd_cost.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 1020s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage6W_causal_teacher_kl_cost -- "$python_bin" -B -X utf8 scripts/diag_p107_causal_kd_cost.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage6W_causal_teacher_kl_cost --note "actual_exit=$result; same resident frozen native teacher in both matched arms. Sixteen full-shape synthetic updates, causal-only KL versus None, repeated trajectory and unchanged teacher required. No corpus, quality or cross-tokenizer claim. Zero checkpoint writes, deadline15:00 KST, final ownedCUDA0."
exit "$result"
