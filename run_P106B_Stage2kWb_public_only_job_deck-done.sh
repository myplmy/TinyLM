#!/usr/bin/env bash
# P106B Stage2kWb: public Aya Dataset/OASST2 jobs only, write-once ignored HF.
# No protected dictionary read, derivative candidate, teacher/model or GPU.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2kWb_public_only_job_deck.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2kWb runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2kWb_public_only_job_deck --num 101 --note \
  'Public Aya Dataset/OASST2 source jobs only in new ignored HF namespace. No protected dictionary read or output, no teacher answer or student training. Source card rights and later model publication remain separate decisions.'
"$python_bin" scripts/runlog.py --name P106B_Stage2kWb_public_only_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_multisource_deck.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2kWb_public_only_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_source_isolation.py
"$python_bin" scripts/runlog.py --name P106B_Stage2kWb_public_only_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_multisource_deck.py --execute
