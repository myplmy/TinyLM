#!/usr/bin/env bash
# P106B Stage2jWb: one-request peg-native parser bypass diagnosis only.
# Full teacher on idle GPU, max five minutes; raw content is NOT a student target.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2jWb_peg_parser_bypass.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2jWb runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2jWb_peg_parser_bypass --num 101 --note \
  'Authorized one-request CPU+GPU forensic: reproduce Stage2f case26 with only --skip-chat-parsing changed. Raw content stays in ignored HF v12; reasoning/final NOT separated, training target0, checkpoint0.'
"$python_bin" scripts/runlog.py --name P106B_Stage2jWb_peg_parser_bypass --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_peg_bypass_probe.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2jWb_peg_parser_bypass --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_peg_bypass_probe.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2jWb_peg_parser_bypass --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_peg_bypass_probe.py --execute
