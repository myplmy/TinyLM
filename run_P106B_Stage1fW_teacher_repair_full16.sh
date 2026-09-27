#!/usr/bin/env bash
# P106B Stage1fW: user-run sixteen-item correction candidate census.
# No student training/checkpoint; actual full-run wall varies with reasoning.
# Requires fresh WSL smoke PASS, GPU idle, and immutable v1/v2/v3 lineage.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1fW_teacher_repair_full16.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1fW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1fW_teacher_repair_full16 --num 101 --note \
  'Prerequisites: user-observed fresh WSL smoke PASS, idle GPU, pinned v1/v2/v3 raw SHA. All 16 original OASST2 pairs are untrusted; teacher may correct or state uncertainty. New ignored v4 retains source/reasoning/final/repair status, never overwrites v1-v3.'
"$python_bin" scripts/runlog.py --name P106B_Stage1fW_teacher_repair_full16 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair_full.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1fW_teacher_repair_full16 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair_full.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1fW_teacher_repair_full16 --num 101 --note \
  'Format gate: at least 12/16 stop+JSON within a hard 3300s. Even if format passes, teacher correction is self-claim, training accept=0. Inspect v4 with independent claim/source review before any student SFT.'
"$python_bin" scripts/runlog.py --name P106B_Stage1fW_teacher_repair_full16 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_answer_repair_full.py --execute
