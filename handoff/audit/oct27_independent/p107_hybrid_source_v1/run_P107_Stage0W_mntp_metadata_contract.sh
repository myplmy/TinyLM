#!/usr/bin/env bash
# Metadata only; reuse the closed 109-test CPU receipt, no model or GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/p107_hybrid_profile_v1.json --profile-sha256 9EF350FC8D5B3814E9AA97C399FC6EE943F2274F0DFD9A74A2A0172CB31EB63C --max-wall-sec 900)
timeout --signal=TERM --kill-after=20s 120s "$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage0W_mntp_metadata_contract --num 107 -- "$python_bin" -B -X utf8 scripts/diag_p107_hybrid_mntp.py "${common[@]}" --check-only
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage0W_mntp_metadata_contract --num 107 --note "Metadata actual_exit=$result; closed109 CPU tests/source/actual tokenizer SHA only. Models0/GPU0/optimizer0/CP0; no training or quality adoption. Timeout8/error9 stay separate."
exit "$result"
