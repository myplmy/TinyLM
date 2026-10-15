#!/usr/bin/env bash
# Completed CPU toy12, raw012235 exit0; shuffle1337 was identity, noted in105.
# Not real model quality, route training or a learned router; product core unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/105_log_$(date +%Y%m%d)_P070B_Stage0Wa_cla_atomic_route_contract_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; new suffix required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wa_cla_atomic_route_contract_"$run_stamp" --num 105 --note 'CPU toy functionality only. Same visit multiset, CLA atomic ownership, cache route lock, causal mask and uniform logits/gradient. Maximum-visit random draw is not random-depth training or learned routing. Actual checkpoint/GPU/optimizer0; product defaults and P106B frozen code unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wa_cla_atomic_route_contract_"$run_stamp" --num 105 -- "$python_bin" -B -X utf8 scripts/diag_p070b_cla_routes.py --execute
