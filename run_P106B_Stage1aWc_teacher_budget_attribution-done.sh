#!/usr/bin/env bash
# P106B Stage1aWc: sandbox-permitted retry of bounded paired teacher attribution.
# The prior Wb launcher stopped before teacher load: NVML denied in sandbox.
# User-approved one-off Codex CPU+GPU execution ceiling: under 10 minutes.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1aWc_teacher_budget_attribution.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1aWc runlog already exists: %s; use a new stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1aWc_teacher_budget_attribution --num 101 --note \
  'Prior Wb failed before teacher load because default sandbox denied NVML. This is a distinct approved GPU-permitted retry. v1 remains read-only; four paired public cases, ctx4096, medium/model-card sampler, cap768 vs3072, new v2 evidence only.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aWc_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1aWc_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1aWc_teacher_budget_attribution --num 101 --note \
  'Read per-arm finish_reason, reasoning_content and final content separately. Only complete final JSON assistant_ko is future student target. Four-case panel is not the 12/16 full gate; no student/model-quality claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aWc_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --execute
