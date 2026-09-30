#!/usr/bin/env bash
# P106B_Stage3jW_corrected_shared_corpus: user-run only. Expected 0.1h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3jW_corrected_shared_corpus.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing runlog preserved: %s. Use a new stage on retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 --note \
  'Prepare corrected common raw corpus after C gate. Keep parent concepts, translated variants and normalized questions together in train/val. Encode each split with its own A/B tokenizer; record actual conversation and assistant tokens. New v29 shards only; no model or GPU.'
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_generate_chat_stops.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode prepare
"$python_bin" scripts/runlog.py --name P106B_Stage3jW_corrected_shared_corpus --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode prepare
