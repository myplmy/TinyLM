#!/usr/bin/env bash
# P106B_Stage3mWe_lineage_pair_contract: expected 0.10h. Both current child reports, checkpoint and fixed answers linked; descriptive only, no cross-tokenizer CE ranking.
# New stage/version only; originals preserved; every prerequisite failure stops this launcher.
# No interactive input. CPU/static success does not imply new teacher/student quality.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3mWe_lineage_pair_contract.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3mWe_lineage_pair_contract --num 101 --note 'Both current child reports, checkpoint and fixed answers linked; descriptive only, no cross-tokenizer CE ranking. Read raw answers and report domains separately. Admission is not truth; no stdin wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage3mWe_lineage_pair_contract --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode compare
"$python_bin" scripts/runlog.py --name P106B_Stage3mWe_lineage_pair_contract --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode compare
