#!/usr/bin/env bash
# P106B Stage2fW: user-run bounded 32-job bilingual teacher pilot.
# Requires Stage2c tagged threshold and Stage2e finite public-v3 job deck.
# Full-GPU teacher, <=42 min, write-once <=20MB raw shards; student SFT 0.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2fW_bilingual_teacher_pilot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2fW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2fW_bilingual_teacher_pilot --num 101 --note \
  'Prerequisites: fresh WSL smoke PASS, idle RTX GPU, Stage2c tagged >=12/16 and Stage2e finite deck. Eight heuristic topics x ko/en x two source IDs; no budget-filling prompt loop.'
"$python_bin" scripts/runlog.py --name P106B_Stage2fW_bilingual_teacher_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_pilot.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2fW_bilingual_teacher_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_pilot.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2fW_bilingual_teacher_pilot --num 101 --note \
  'Gate: >=12 tagged-format/canonical screened candidates in each language; exact/near duplicate rejection and per-language student/teacher tokens and wall are measured. Raw reasoning/final remain separate; no truth or 300M claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage2fW_bilingual_teacher_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_pilot.py --execute
