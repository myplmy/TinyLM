#!/usr/bin/env bash
# Synthetic BF16 logits; no model/optimizer/corpus/checkpoint operations.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/p107_argmax_profile_v1.json --profile-sha256 398DD791EA5DC6B81941609923AD03B6A89D7CDD723E247FB6E034A362AE4886 --max-wall-sec 300)
"$python_bin" -B -X utf8 scripts/diag_p107_adaptive_gpu_transfer.py "${common[@]}" --check-only
preflight=$?
if (( preflight != 0 )); then exit "$preflight"; fi
timeout --signal=TERM --kill-after=20s 360s "$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage3W_argmax_transfer_cost --num 107 -- "$python_bin" -B -X utf8 scripts/diag_p107_adaptive_gpu_transfer.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage3W_argmax_transfer_cost --num 107 --note "GPU actual_exit=$result; known synthetic BF16 maxima only,32K/262K full/gathered argmax+CPUstats. Models0/training0/optimizer0/corpus0/CP0; no model coexistence, fusedCE, learning speed or quality adoption. Error9/HOLD8 remain separate; raw/profile/source preserved."
exit "$result"
