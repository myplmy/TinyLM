#!/usr/bin/env bash
# Original production payloads, two reversed OFF/ON orders; no auto policy change.
# Requires the frozen successful family64 source and idle teacher-only GPU.
# Expected about15-30min, hard cap1800s; source/old evidence stay read-only.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
name=P106B_Stage6eWb_mtp_production_order_pair
log="test_result/101_log_$(date +%Y%m%d)_${name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWb_mtp_production_order_pair --num 101 --note 'Frozen source/question/history/sampler/seed OFF-ON then ON-OFF. Every original raw and reasoning retained below20MB; shared max3 structural attempts. Read actual answers and source after collection; no online semantic phrase filter, student, training or automatic production adoption.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWb_mtp_production_order_pair --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_gemma_mtp_production.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage6eWb_mtp_production_order_pair --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_mtp_production.py --tag p106b_gemma_mtp_production_order_v1_s1337 --rounds 2 --protocol production --max-wall-sec 1800 --execute
