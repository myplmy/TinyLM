#!/usr/bin/env bash
# P106B Stage1aWb: paired teacher completion-cap attribution on four public pairs.
# User-approved one-off Codex CPU+GPU execution ceiling: under 10 minutes.
# No student loading, no SFT, no checkpoint; immutable v1 is read-only.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1aWb_teacher_budget_attribution.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1aWb runlog already exists: %s; use a new stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1aWb_teacher_budget_attribution --num 101 --note \
  'Four pinned public OASST2 pairs: prior v1 incomplete3/control complete1. Same ctx4096, medium reasoning and explicit Bonsai thinking sampler; only max_tokens768 vs3072 changes within pair. v1 read-only; raw reasoning/final separated in new ignored v2.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aWb_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1aWb_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1aWb_teacher_budget_attribution --num 101 --note \
  'Read finish_reason and per-arm JSON_COMPLETE/usage/timing; 4-pair selected panel is NOT a 12/16 population gate. Student training and quality remain NOT_RUN. Exit8 is bounded resource/time negative, exit9 tool fault.'
"$python_bin" scripts/runlog.py --name P106B_Stage1aWb_teacher_budget_attribution --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_budget_attribution.py --execute
