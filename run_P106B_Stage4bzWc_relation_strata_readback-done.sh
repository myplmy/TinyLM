#!/usr/bin/env bash
# CPU only. Actual self-history, supplied error, gold history remain separate.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bzWc_relation_strata_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzWc_relation_strata_readback_"$run_stamp" --num 101 --note 'CPU5 then history/field/language raw recount and root-weighted intervals. No model loading, truth judgment, automatic exclusion or TEST-selected checkpoint. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzWc_relation_strata_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_strata.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzWc_relation_strata_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_strata.py --execute
