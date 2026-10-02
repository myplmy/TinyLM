#!/usr/bin/env bash
# P106B_Stage3sWb_fp32_cache_recheck: expected 0.10h. Only the six observed A BF16 cache differences, FP32 forward/shadow and TF32 disabled; no training or teacher, hard300s.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3sWb_fp32_cache_recheck.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3sWb_fp32_cache_recheck --num 101 --note 'Only the six observed A BF16 cache differences, FP32 forward/shadow and TF32 disabled; no training or teacher, hard300s.'
"$python_bin" scripts/runlog.py --name P106B_Stage3sWb_fp32_cache_recheck --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_cache_fp32_recheck.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3sWb_fp32_cache_recheck --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_cache_fp32_recheck.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3sWb_fp32_cache_recheck --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_cache_fp32_recheck.py --execute

