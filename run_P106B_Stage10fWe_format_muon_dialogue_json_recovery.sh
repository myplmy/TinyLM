#!/usr/bin/env bash
# Authorized26Oct2026: fixed12 questions xplain/ChatML after actual full300M.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
helper="handoff/audit/oct26_research/run_native_dialogue.py"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 "$helper" --arm format_muon --check-only
fi
exec timeout --signal=TERM --kill-after=10s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10fWe_format_muon_dialogue_json_recovery -- "$python_bin" -B -X utf8 "$helper" --arm format_muon
