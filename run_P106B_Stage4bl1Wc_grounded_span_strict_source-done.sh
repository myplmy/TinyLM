#!/usr/bin/env bash
# New pre-GPU phase: strict RNG plus explicit phase/arm dispatch validation.
# Reuses immutable v1 data; v2 CPU-only contract preserved, actual student tag v3.
# No stdin, downloads, old writes, queue, cleanup, smoke or publication.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bl1Wc_grounded_span_strict_source_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve previous raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bl1Wc_grounded_span_strict_source_"$run_stamp" --num 101 --note 'New strict RNG/explicit dispatch contract v3. Source v1 unchanged; v2 had CPU-only execution and AST delegation ambiguity, not failed model learning. Read actual source/assistant/native counts and free answers separately. Authority until Oct16 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bl1Wc_grounded_span_strict_source_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_grounded_span_execution.py --mode freeze --execute --max-wall-sec 600
