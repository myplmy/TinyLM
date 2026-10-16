#!/usr/bin/env bash
# Completed 2026-10-16 15:10:20 KST; raw151013 exits0, CPU5 and64 inputs.
# Same-fact question wording control; not new training or a memory feature.
# CPU seconds or bounded600 GPU seconds, one model at a time.
# Only this stage's prerequisites fail closed. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4df0W_evidence_style_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a fresh stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4df0W_evidence_style_cpu_"$run_stamp" --num 101 --note 'CPU5/frozen32 two wordings, no forward/CUDA. Same known facts and whole64 output budget; posthoc not new TEST. Raw/weights private below20MB shards. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4df0W_evidence_style_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_style.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4df0W_evidence_style_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_style.py --mode freeze --execute
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4df0W_evidence_style_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_style.py --mode evaluate --check-only
