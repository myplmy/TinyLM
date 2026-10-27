#!/usr/bin/env bash
# Corrected CPU-only resume invariants; preserve the first actual result.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/p107_adaptive_profile_v3.json --profile-sha256 FF4B48A6F7E5F8779232B0E814B8C7F0E002E07020BAB14D53E1C6D4A2E9DB25 --max-wall-sec 300)
"$python_bin" -B -X utf8 scripts/diag_p107_adaptive_masking.py "${common[@]}" --check-only
preflight=$?
if (( preflight != 0 )); then exit "$preflight"; fi
timeout --signal=TERM --kill-after=20s 360s "$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage2Wb_adaptive_resume_recovery --num 107 -- "$python_bin" -B -X utf8 scripts/diag_p107_adaptive_masking.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage2Wb_adaptive_resume_recovery --num 107 --note "CPU actual_exit=$result; corrected longEMA/firstwindow resume,27closed tests,six synthetic cases. Models0/GPU0/optimizer0/CP0/corpus0; no quality/speed/bias adoption. Profilev2 was prepared only, NOT_RUN; v1 actual preserved."
exit "$result"
