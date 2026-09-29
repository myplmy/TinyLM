#!/usr/bin/env bash
# P106B Stage2iWb / option B: five bounded online updates, no reasoning.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWb_online5_none.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2iWb log exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWb_online5_none --num 101 --note \
  'Option B none: model-card instruct sampler, unlike earlier Stage2h none thinking-sampler timing. Five micro8*accum16 updates need 640 fresh accepted teacher answers. 90min cap, P076 parent, full teacher, write-once <=20MB HF shards, no checkpoint or formal SFT quality claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWb_online5_none --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWb_online5_none --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort none
"$python_bin" scripts/runlog.py --name P106B_Stage2iWb_online5_none --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort none --max-wall-sec 5400
