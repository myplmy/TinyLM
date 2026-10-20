#!/usr/bin/env bash
# P106B_Stage4foWg_native595_public_readback: same public pack/scorer, explicit new strict providers, no new training.
# All six real endpoints must complete before prepare. No partial-set fallback or old evidence retag.
# FP32-MATH/KV-on/MTP-off greedy128; closed execution is not general intelligence.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This immutable stage accepts no positional arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4foWg_native595_public_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw is preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4foWg_native595_public_readback_"$run_stamp" --num 101 --note 'Native5952/oldBroad2/newBroad2 explicit trained-route providers; all six exact completed CP/report/source refs required. Same frozen public9216 requested/9212 scored, length exclusions4; native eachEnglish768, four students each1920/1919. Same FP32-MATH/KV-on/MTP-off/greedy128/context1024, SUM_NLL primary and char diagnostic, no PMI. CachedFalcon398/768 reused only. Family actual-worker3600/maxworker1800/record600 and21st17KST; current stage readback cap600s. No stdin/download/teacher/Git/old overwrite; every public file below20MB. Valid incomplete upstream HOLD differs from damaged evidence ERROR. No general-conversation or architecture-only causal claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4foWg_native595_public_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595_public.py --mode readback --max-wall-sec 600 --execute
