#!/usr/bin/env bash
# P106B_Stage4aW_mixed_public_corpus: expected 0.75h. CPU public-only source-SHA and source-family selection to 37.5M train tokens per language; partial corpus and teacher deficit are explicit, no model/download/semantic approval.
# User execution only; no interactive input. New write-once output version.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4aW_mixed_public_corpus.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4aW_mixed_public_corpus --num 101 --note 'CPU public-only source-SHA and source-family selection to 37.5M train tokens per language; partial corpus and teacher deficit are explicit, no model/download/semantic approval.'
"$python_bin" scripts/runlog.py --name P106B_Stage4aW_mixed_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mixed_scale.py
"$python_bin" scripts/runlog.py --name P106B_Stage4aW_mixed_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_mixed_scale.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage4aW_mixed_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_mixed_scale.py --execute
