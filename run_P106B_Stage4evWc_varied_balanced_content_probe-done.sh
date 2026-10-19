#!/usr/bin/env bash
# Final-fit versus surface-transfer diagnostic; no training, optimizer, or checkpoint writes.
# Same existing endpoints and exact frozen wire projection; no new natural/native source audit.
# FP32-MATH greedy0 topk1 KV-on MTP-off max64; user-only generation, gold is TF/readout only.
# evaluate worker limit600s; GPU total5-10min estimated across three models; idle intervals are separate.
# Full raw stdout/stderr is preserved by runlog; only the GPT tool-return view is compacted.
# REGRESSION then source/preflight then EXECUTE; independent queue entries continue on failure.
# HOLD8, ERROR9, and interrupt130 are not model-quality verdicts; no stdin waits.
# Read per-family content/EOT and actual answers; no broad-intelligence or75M-completion claim.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4evWc_varied_balanced_content_probe_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4evWc_varied_balanced_content_probe_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_question_content_probe.py --mode evaluate --endpoint varied_balanced --max-wall-sec 600 --execute
