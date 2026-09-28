#!/usr/bin/env bash
# P106B Stage2iWd: one online optimizer update, original OASST1 source lineage.
# Requires Stage2fWb PASS; known PEG 500 is recorded/rejected, unknown HTTP is exit9.
# This is a technical backend pilot, no checkpoint or model-quality claim.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWd_online1_backend.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2iWd runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWd_online1_backend --num 101 --note \
  'Original Stage2iWa used OASST1 from public-v3, not OASST2. This one-update technical recovery uses the same source/parent/low sampler after Stage2fWb PASS. Known PEG 500 is a rejected attempt; unknown API failure is tool exit9. New v13 raw/canonical, no checkpoint or quality claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWd_online1_backend --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate1.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWd_online1_backend --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate1.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2iWd_online1_backend --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate1.py --execute
