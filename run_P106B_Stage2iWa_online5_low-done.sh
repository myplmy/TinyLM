#!/usr/bin/env bash
# P106B Stage2iWa / option A: five bounded online updates, low effort.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWa_online5_low.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2iWa log exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWa_online5_low --num 101 --note \
  'Option A low: model-card thinking sampler; low is described as unsupported/near xhigh by the current card. Five micro8*accum16 updates need 640 fresh accepted teacher answers. 4h cap, P076 parent, full teacher, write-once <=20MB HF shards, no checkpoint or formal SFT quality claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWa_online5_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWa_online5_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort low
"$python_bin" scripts/runlog.py --name P106B_Stage2iWa_online5_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort low --max-wall-sec 14400
