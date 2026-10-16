#!/usr/bin/env bash
# Closed final CPU36 plus real call/saved smoke receipt checks; no model/GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4emWc_final_audit_contract_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4emWc_final_audit_contract_cpu_"$run_stamp" --num 101 --note 'CPU36 scope/profile regressions, real repository call signatures and unchanged final44 smoke receipt. No models/GPU/new smoke/training. Original static errors retained in FINAL audit.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4emWc_final_audit_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_check_call_kwargs_scope scripts.test_smoke_diag_freshness
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4emWc_final_audit_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/check_call_kwargs.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4emWc_final_audit_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/check_smoke_diag.py
