#!/usr/bin/env bash
# Authorized26Oct2026: full Core6 only after closed300M checkpoint.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TQDM_DISABLE=1 TL_WANDB_AUTO=0
helper="handoff/audit/oct26_research/run_native_official.py"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 "$helper" --arm format_muon --check-only
fi
exec timeout --signal=TERM --kill-after=10s 8670s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10eWe_format_muon_official_json_recovery -- "$python_bin" -B -X utf8 "$helper" --arm format_muon
