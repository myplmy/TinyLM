#!/usr/bin/env bash
# Authorized26Oct2026: frozen full300M native optimizer pair; no teacher coload.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
helper="handoff/audit/oct26_research/run_native_training.py"
if [[ "${1:-}" == --check-only ]]; then
  shift
  exec "$python_bin" -B -X utf8 "$helper" --mode train --arm format_normuon --check-only "$@"
fi
exec timeout --signal=TERM --kill-after=10s 14490s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10dWc_format_normuon_train -- "$python_bin" -B -X utf8 "$helper" --mode train --arm format_normuon --execute "$@"

