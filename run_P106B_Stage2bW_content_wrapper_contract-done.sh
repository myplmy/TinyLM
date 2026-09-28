#!/usr/bin/env bash
# P106B Stage2bW: CPU-only teacher-text -> canonical/ChatML boundary gate.
# The teacher never writes role IDs, ChatML, tokenizer IDs or loss labels.
# No model load, new dataset, checkpoint or training.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2bW_content_wrapper_contract.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2bW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2bW_content_wrapper_contract --num 101 --note \
  'CPU contract: tagged teacher fields, code-owned roles/provenance and existing TinyLM canonical/ChatML assistant-only labels; raw reasoning stays SHA-bound sidecar, dataset files stay <=20MB.'
"$python_bin" scripts/runlog.py --name P106B_Stage2bW_content_wrapper_contract --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_teacher_format.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2bW_content_wrapper_contract --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_teacher_wrapper.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2bW_content_wrapper_contract --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_shards.py --self-test
