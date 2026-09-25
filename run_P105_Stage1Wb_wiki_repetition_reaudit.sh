#!/usr/bin/env bash
# P105 Stage1Wb: re-audit the existing 280-answer JSONL only; ~0.1 h, CPU/no model.
# Failure or incomplete 7 x 40 panel stops the gate. Manual semantic quality remains NOT_RUN.
# Read-only input; the original Stage1W result and JSONL are never rewritten.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
input=runs/bench/p105_stage1w_wiki_panel_7model.jsonl
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1Wb_wiki_repetition_reaudit --note "Original Stage1W repeat_heuristic=22 undercounts one-character and phrase loops. Re-audit same 280 answers only; model/source/semantic quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1Wb_wiki_repetition_reaudit -- "$python_bin" -B -X utf8 scripts/diag_p105_repetition_reaudit.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] P105 Stage1Wb fixture rc=%s\n' "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1Wb_wiki_repetition_reaudit -- "$python_bin" -B -X utf8 scripts/diag_p105_repetition_reaudit.py --input-jsonl "$input"
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] P105 Stage1Wb saved-answer audit rc=%s; do not treat as 280-row PASS\n' "$rc" >&2
    exit "$rc"
fi
printf '[PASS] P105 Stage1Wb repeat candidates recorded in 097 log; inspect raw answers before a quality claim\n'
