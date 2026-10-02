#!/usr/bin/env bash
# P106B_Stage4cW_mixed_chat32_repeat4: expected 12h, conditional on actual75M train tokens and separate val.
# User GPU only, teacher down first, micro8/accum16/checkpoint-on/four actual passes.
# This is experimental SFT, not formal data-quality approval. No interactive input.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cW_mixed_chat32_repeat4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4cW_mixed_chat32_repeat4 --num 101 --note 'Actual75M nonpadding train token prerequisite, language quotas, native/answer before-after, micro8/accum16/ckpt-on/4passes; teacher down.'
"$python_bin" scripts/runlog.py --name P106B_Stage4cW_mixed_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mixed_scale.py
"$python_bin" scripts/runlog.py --name P106B_Stage4cW_mixed_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage4cW_mixed_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --execute
