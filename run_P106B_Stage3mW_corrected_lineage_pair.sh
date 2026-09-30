#!/usr/bin/env bash
# P106B_Stage3mW_corrected_lineage_pair: user-run only. Expected 0.1h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3mW_corrected_lineage_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing runlog preserved: %s. Use a new stage on retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 --note \
  'Pair A/B common-corpus evidence and exact checkpoints after both4epoch arms. Keep first attempt separate from best within3. Compare same fixed question raw answers and own-cache before/after, not cross-tokenizer CE. No GPU/model loading; manual semantic review remains.'
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_generate_chat_stops.py
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode compare
"$python_bin" scripts/runlog.py --name P106B_Stage3mW_corrected_lineage_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode compare
