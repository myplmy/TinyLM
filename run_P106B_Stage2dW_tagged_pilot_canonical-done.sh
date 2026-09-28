#!/usr/bin/env bash
# P106B Stage2dW: CPU-only v6 tagged result to versioned canonical pilot.
# Requires Stage2cW user result, tagged >=12/16 and fixed val cases 2/15.
# Output v7 HF shards are write-once and <=20MB each; no student/model GPU.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2dW_tagged_pilot_canonical.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2dW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2dW_tagged_pilot_canonical --num 101 --note \
  'Prerequisite Stage2cW v6 teacher log/manifest and fixed val cases. Canonical wrapper is code-owned; raw reasoning remains a SHA-bound sidecar and never an active SFT target.'
"$python_bin" scripts/runlog.py --name P106B_Stage2dW_tagged_pilot_canonical --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_tagged_pilot.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2dW_tagged_pilot_canonical --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_tagged_pilot.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2dW_tagged_pilot_canonical --num 101 --note \
  'Gate: >=12 tagged valid cases and fixed val cases; write-once train/val canonical shards <=20MB with hashes. Dataset stays PSEUDO_UNVERIFIED, tiny Korean-only pilot, no 300M/600M or student training claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2dW_tagged_pilot_canonical --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_tagged_pilot.py --execute
