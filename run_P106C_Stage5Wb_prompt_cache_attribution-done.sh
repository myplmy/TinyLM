#!/usr/bin/env bash
# P106C A recovery: identical frozen models/grid; preserve first OS-denied attempt.
# Explicit current-user CPU/GPU permission for A only; hard wall900s, no updates.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage5Wb_prompt_cache_attribution.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage5Wb_prompt_cache_attribution --num 102 --note 'A runtime recovery only; first NVML OS denial preserved; same3 models/64 prompts/cache pairs,900s cap, zero updates/checkpoint writes.'
"$python_bin" scripts/runlog.py --name P106C_Stage5Wb_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_followup.py
"$python_bin" scripts/runlog.py --name P106C_Stage5Wb_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_prompt_cache.py --check-only --mode recovery
"$python_bin" scripts/runlog.py --name P106C_Stage5Wb_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_prompt_cache.py --execute --mode recovery
