#!/usr/bin/env bash
# Complete576 teacher records required; supported-only512/64 corpus. About0.03h CPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj3W_supported_source_corpus_"$stamp" --note 'Freeze supported-only512/64. Do not create a missing-reference half. Preserve source/question/answer/reasoning lineage; semantic truth remains pseudo and75M admission is not automatic.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj3W_supported_source_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_expand.py --mode corpus --execute
