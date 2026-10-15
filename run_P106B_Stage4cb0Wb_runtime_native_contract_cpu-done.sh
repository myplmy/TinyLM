#!/usr/bin/env bash
# V2 native runtime recovery, v1 data/CODE/raw immutable, no stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cb0Wb_runtime_native_contract_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0Wb_runtime_native_contract_cpu_"$run_stamp" --num 101 --note 'CPU8: reproduce preserved missing marker, actual16 read-only native windows versus original, same training AST. No model or cache copies. Not75M/300M or world intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0Wb_runtime_native_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_native_contract_v2.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0Wb_runtime_native_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_train_v2.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0Wb_runtime_native_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_runtime_v2.py --execute
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0Wb_runtime_native_contract_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_train_v2.py --mode cost --arm fact1 --check-only
