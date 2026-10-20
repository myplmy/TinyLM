#!/usr/bin/env bash
# P106B_Stage4fhWe_resume_broad_mixed_public: explicit six-model provenance bridge; original evaluator and scoring preserved.
# Prepare requires both native, both resume SFT and both bounded Broad endpoints complete.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fhWe_resume_broad_mixed_public_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fhWe_resume_broad_mixed_public_"$run_stamp" --num 101 --note 'Current public benchmark resume21KST. Six exact completed models required; native original, SFT resume_v2, Broad resume_v3 with original P090B parent. Fixed public pack and cached Falcon only; no new Falcon/download/training/CP. Same requested9216/scored9212, original length skips, primary SUM_NLL and secondary char-normalized. FP32-MATH/greedy128/KV-on/MTP-off. Total active3600/record600 and original aux-worker dedup, worker cap1200s. Completion is not official-harness parity, decontamination or general-intelligence proof; files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fhWe_resume_broad_mixed_public_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_current_benchmark_resume.py --mode evaluate --model-id broad_mixed --max-wall-sec 1200 --execute
