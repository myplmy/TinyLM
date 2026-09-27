#!/usr/bin/env bash
# P106B Stage1aW: user-run, bounded full-GPU Bonsai Korean translation gate.
# About 0.5 h maximum; requires a fresh WSL smoke PASS and an idle 16 GiB GPU.
# This produces review-only candidates, not approved training examples.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1aW_oasst2_teacher_ko_gate.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1aW runlog already exists: %s; use a new stage suffix for retries.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1aW_oasst2_teacher_ko_gate --num 101 --note \
  'Prerequisite: user-observed fresh WSL smoke PASS; idle GPU. Source OASST2 pinned; output new HF/sft_ready/p106b_teacher_sft/v1 candidate JSONL only. JSON_COMPLETE is not P106 verified ACCEPT.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aW_oasst2_teacher_ko_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_oasst2_teacher_ko_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1aW_oasst2_teacher_ko_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_oasst2_teacher_ko_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1aW_oasst2_teacher_ko_gate --num 101 --note \
  'Pass: >=12/16 complete Korean JSON pairs within 1800s, free GPU pre>=8192MiB/post>=2048MiB. Exit8 is a gate-negative; exit9 is a tool fault. All rows remain UNKNOWN and student learning=0.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aW_oasst2_teacher_ko_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_oasst2_teacher_ko_gate.py --execute
