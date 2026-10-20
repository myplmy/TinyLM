#!/usr/bin/env bash
# P106B_Stage4fmWh_native595_pair_readback: measured-admission native595 matched Q/F pair, not a tokens-only old299M contrast.
# Explicit4543x8x16x1024, same scratch/source/crops, original native WSD/Muon/clip1/grad-checkpoint.
# Worker cap from actual paired8 costs; no stdin/download/old overwrite or semantic auto-adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ $# -ne 0 ]]; then
    printf '%s\n' '[STOP] This immutable stage accepts no arguments.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fmWh_native595_pair_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWh_native595_pair_readback_"$run_stamp" --num 101 --note 'Native595 closed paired-cost budget required and recalculated before each train. Main595460096 targets/crops581504 in exact1191116192 pool; same fresh028C46. Original Q uses original STE window even at anneal0; F uses identity gradients, so route package is not pure rounding-only. Original AdamW/Muon2D RMS/clip1/ckpt-on/BF16/default compile. Native end21st11:30KST/followup7200/eval1200/record600/global14KST train/17KST authority; active43200, max native18000. Mode readback cap900s. Closed actual worker then readonly VERIFY required for train; weight-only is not exact resume. Native32 is not wholeVAL, conversation or Falcon parity. Public files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWh_native595_pair_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595.py --mode readback --max-wall-sec 900 --execute
