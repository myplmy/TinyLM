#!/usr/bin/env bash
# Seal native scope admission after CPU span and frozen-source checks.
# CPU metadata/tokenizer only; under2min expected; old scope sources immutable.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_native preflight
fi
"$python_bin" -B -m scripts.diag_p108c_native preflight || exit $?
timeout --signal=TERM --kill-after=20s 1230s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage1Wa_native_scope_prepare_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_native prepare
exit $?
