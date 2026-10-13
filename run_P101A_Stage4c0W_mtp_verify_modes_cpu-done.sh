#!/usr/bin/env bash
# CPU regression; actual K, rejection cache prefixes, CLA/R2 and stop; no model assets
# Estimated 0.02h; no stdin, download, old overwrite or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage4c0W_mtp_verify_modes_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4c0W_mtp_verify_modes_cpu_"$run_stamp" --num 092 --note 'CPU regression; actual K, rejection cache prefixes, CLA/R2 and stop; no model assets. Original v2 retained; read actual K/mode/precision and full answers. GPT runtime authorization ends 2026-10-14 17:00 KST; later user-run only.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4c0W_mtp_verify_modes_cpu_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p101a_mtp_parity scripts.test_p101a_sft_mtp
