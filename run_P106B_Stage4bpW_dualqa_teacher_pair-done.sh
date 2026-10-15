#!/usr/bin/env bash
# Same8 reference sources,1/2QA in both orders. Teacher MTP ON; no student training.
# Content labels only, code-owned wrapping; shared3 structural attempts, no word blacklist.
# Source/reasoning/final preserved separately, no stdin/download/original mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bpW_dualqa_teacher_pair_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve previous raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bpW_dualqa_teacher_pair_"$run_stamp" --num 101 --note 'Same-source1QA/2QA measurement, not an effort or semantic-truth comparison. Gemma MTP2, thinking256 at server/request, ctx8192/output3072, same sampler/seed policy. Code owns canonical/ChatML. Raw32 plus bounded retries, candidate conversations may contain1/2 assistant turns. Pilot repeated sources are not training data. Deadline Oct16 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bpW_dualqa_teacher_pair_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_teacher.py --execute --max-wall-sec 3600
