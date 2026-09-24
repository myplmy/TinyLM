#!/usr/bin/env bash
# P105 Stage0W: CPU-only wiki tail/generation contract, about 0.1 h; no HF/model/GPU.
# Failure stops this gate; success is structural, not scientific quality.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage0W_wiki_format_contract --note "Synthetic source/generation JSONL counters only; actual wiki source and model behavior NOT_RUN."
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage0W_wiki_format_contract -- "$python_bin" -B -X utf8 scripts/diag_p105_wiki_format.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] P105_Stage0W_wiki_format_contract rc=%s\n' "$rc" >&2
    exit "$rc"
fi
printf '[PASS] P105_Stage0W_wiki_format_contract fixture complete; dynamic source/teacher/model evidence NOT_RUN\n'
