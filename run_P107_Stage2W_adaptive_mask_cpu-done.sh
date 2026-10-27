#!/usr/bin/env bash
# Synthetic CPU policy contracts and costs; no corpus, model, training or GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/p107_adaptive_profile_v1.json --profile-sha256 0AF4A34D435FFEE04A777E6916B26F5B2D265E60DB8BEB6F1CA4DE8C6A83BDAC --max-wall-sec 300)
"$python_bin" -B -X utf8 scripts/diag_p107_adaptive_masking.py "${common[@]}" --check-only
preflight=$?
if (( preflight != 0 )); then exit "$preflight"; fi
timeout --signal=TERM --kill-after=20s 360s "$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage2W_adaptive_mask_cpu --num 107 -- "$python_bin" -B -X utf8 scripts/diag_p107_adaptive_masking.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage2W_adaptive_mask_cpu --num 107 --note "CPU actual_exit=$result; synthetic32K/262K uniform/keep/prior,25closed tests. Models0/GPU0/optimizer0/CP0/corpus0; no intelligence, language bias or training speed adoption. Policy-only resume; caller training resume remains unfinished."
exit "$result"
