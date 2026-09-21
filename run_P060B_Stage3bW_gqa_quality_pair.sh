#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
name="P060B_Stage3bW_gqa_quality_pair"
"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage3bW_gqa_quality_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M \
    --models p060b_q_off_s1337 p060b_q_on_s1337 \
    --dump-crops runs/logs/p060b_gqa_quality_s1337.json || exit $?
"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage3bW_gqa_quality_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M \
    --models p060b_q_off_s2024 p060b_q_on_s2024 \
    --dump-crops runs/logs/p060b_gqa_quality_s2024.json || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage3bW_gqa_quality_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M \
    --models p060b_q_off_s31415 p060b_q_on_s31415 \
    --dump-crops runs/logs/p060b_gqa_quality_s31415.json
