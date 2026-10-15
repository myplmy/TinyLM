#!/usr/bin/env bash
# Completed seed0 nonidentity CPU5, raw012851 exit0; oldWa unchanged.
# Old Stage0Wa identity draw/code/report preserved; no real checkpoint or GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/105_log_$(date +%Y%m%d)_P070B_Stage0Wb_cla_nonidentity_shuffle_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wb_cla_nonidentity_shuffle_"$run_stamp" --num 105 --note 'Declared nonidentity seed0 CPU toy coverage. Full/decode cache, actual shuffled checkpoint gradient, causality and route cache lock; previous uniform seed1337 record unchanged. Real checkpoint/GPU/optimizer0; no architecture quality or learned-router claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wb_cla_nonidentity_shuffle_"$run_stamp" --num 105 -- "$python_bin" -B -X utf8 scripts/diag_p070b_cla_nonidentity.py --execute
