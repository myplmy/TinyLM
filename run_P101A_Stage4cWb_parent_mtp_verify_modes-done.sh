#!/usr/bin/env bash
# Saved parent MTP; same native and three verify modes; output parity is not semantic quality
# Estimated 0.15h; no stdin, download, old overwrite or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage4cWb_parent_mtp_verify_modes_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4cWb_parent_mtp_verify_modes_"$run_stamp" --num 092 --note 'Saved parent MTP; same native and three verify modes; output parity is not semantic quality. Original v2 retained; read actual K/mode/precision and full answers. GPT runtime authorization ends 2026-10-14 17:00 KST; later user-run only.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4cWb_parent_mtp_verify_modes_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_mtp_parity.py --arm parent_mtp --tag p101a_mtp_parity_v3_s1337 --verify-modes parallel_rebuild parallel_truncate serial_truncate --max-wall-sec 900 --execute
