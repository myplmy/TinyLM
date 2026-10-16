#!/usr/bin/env bash
# Original task direction: preserve unknown contracts, explicitly derive new QA.
# Independent bounded diagnostic; CPU seconds, teacher at most10 minutes.
# Stop only this stage on failed prerequisites. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cx0W_original_task_contract_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cx0W_original_task_contract_cpu_"$run_stamp" --num 101 --note 'CPU10 original pair byte preservation and explicit role ownership. No model forward or CUDA. Original data/weights unchanged. Full raw/thinking private shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cx0W_original_task_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_source_task_contract.py
