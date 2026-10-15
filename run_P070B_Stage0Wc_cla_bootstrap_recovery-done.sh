#!/usr/bin/env bash
# Completed v3 CPU17/direct import, raw013651 exit0; recovery eea62c0.
# Only process-local ROOT path added; body bytes without bootstrap match Git.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/105_log_$(date +%Y%m%d)_P070B_Stage0Wc_cla_bootstrap_recovery_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wc_cla_bootstrap_recovery_"$run_stamp" --num 105 --note 'New v3 after helper direct-import ROOT bootstrap only. Verify byte equivalence against old Git snapshot, direct import and previous12 plus nonidentity5 CPU contracts. Original reports unchanged. Actual checkpoint/GPU/optimizer0; not language or learned-route quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage0Wc_cla_bootstrap_recovery_"$run_stamp" --num 105 -- "$python_bin" -B -X utf8 scripts/diag_p070b_cla_bootstrap.py --execute
