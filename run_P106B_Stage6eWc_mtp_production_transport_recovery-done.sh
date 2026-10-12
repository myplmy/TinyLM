#!/usr/bin/env bash
# Why6eWc: Wa mistakenly required teacher QUESTION to include learner JSON envelope.
# Recover separate teacher question/student request; independent failed rows do
# not block the ON arm. Prior source/log/evidence stay unchanged.
# Remaining authorized direct gate390s; no student or checkpoint; no stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6eWc_mtp_production_transport_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWc_mtp_production_transport_recovery --num 101 --note 'Wa question/wrapper mismatch is preserved as a diagnostic design error, not MTP failure/OOM. Six frozen transport questions and old student output contracts, fresh OFF/ON. Max390s within remaining direct10min authority. Structures and semantic quality remain separate.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWc_mtp_production_transport_recovery --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_gemma_mtp_production.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWc_mtp_production_transport_recovery --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_mtp_production.py --tag p106b_gemma_mtp_production_transport_v2_s1337 --rounds 1 --max-wall-sec 390 --execute
