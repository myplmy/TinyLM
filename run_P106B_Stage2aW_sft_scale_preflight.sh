#!/usr/bin/env bash
# P106B Stage2aW: CPU-only teacher/student token-denominator preflight.
# Cost sample is 16 unverified Korean v4 candidates, not a production rate.
# No teacher/student model load, corpus creation, checkpoint or training.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2aW_sft_scale_preflight.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2aW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2aW_sft_scale_preflight --num 101 --note \
  'Read-only v4 Korean 16-case cost sample. Distinguish teacher completion, serialized student corpus, assistant supervised tokens and training positions; 300M/600M extrapolation is not a forecast.'
"$python_bin" scripts/runlog.py --name P106B_Stage2aW_sft_scale_preflight --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_scale_preflight.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2aW_sft_scale_preflight --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_scale_preflight.py --check-only
