#!/usr/bin/env bash
# P106B Stage1dW: three public English answers as untrusted teacher repair input.
# One-off user-approved Codex CPU+GPU test under ten minutes; no student SFT.
# Immutable teacher v1/v2 are read-only; new v3 stores reasoning and final apart.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1dW_teacher_answer_repair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1dW runlog already exists: %s; use a new stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1dW_teacher_answer_repair --num 101 --note \
  'Known WebRTC source error, stale model-self claim, and verified arithmetic control; teacher repairs English answer into Korean JSON. Medium thinking, official sampler, ctx6144/max4096, thinking budget2048. Original v1/v2 immutable; new ignored v3 retains source/reasoning/final/correction separately.'
"$python_bin" scripts/runlog.py --name P106B_Stage1dW_teacher_answer_repair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1dW_teacher_answer_repair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1dW_teacher_answer_repair --num 101 --note \
  'At least 2/3 complete JSON is a FORMAT gate only. Teacher correction_status is self-claim, never independent truth. No student target is accepted or trained in this run.'
"$python_bin" scripts/runlog.py --name P106B_Stage1dW_teacher_answer_repair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair.py --execute
