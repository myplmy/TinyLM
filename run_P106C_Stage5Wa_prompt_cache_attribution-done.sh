#!/usr/bin/env bash
# P106C Stage5Wa: three frozen checkpoints; no updates or checkpoint writes.
# A only: user approved Codex CPU/GPU diagnostic, hard wall900s. No interactive input.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage5Wa_prompt_cache_attribution.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage5Wa_prompt_cache_attribution --num 102 --note 'Approved A diagnostic only; frozen3 subjects,64 prompts, cache pair; zero updates/checkpoint writes;900s cap.'
"$python_bin" scripts/runlog.py --name P106C_Stage5Wa_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_followup.py
"$python_bin" scripts/runlog.py --name P106C_Stage5Wa_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_prompt_cache.py --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage5Wa_prompt_cache_attribution --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_prompt_cache.py --execute
