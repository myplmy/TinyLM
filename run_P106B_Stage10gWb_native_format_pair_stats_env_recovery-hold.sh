#!/usr/bin/env bash
# Authorized26Oct2026: CPU-only paired readback after both complete Core6 runs.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
helper="handoff/audit/oct26_research/run_native_stats.py"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 "$helper" --check-only
fi
exec timeout --signal=TERM --kill-after=5s 640s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10gWb_native_format_pair_stats_env_recovery -- "$python_bin" -B -X utf8 "$helper"
