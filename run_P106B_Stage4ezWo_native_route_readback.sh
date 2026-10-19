#!/usr/bin/env bash
# P106B_Stage4ezWo_native_route_readback: same scratch initialization and data, ternary versus latent-float TLinear.
# Native m8a16seq1024ckptON, 2281 updates; own-route SFT384. Fail dependent stage only.
# No stdin, download, old mutation, or automatic model-quality verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ezWo_native_route_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ezWo_native_route_readback_"$run_stamp" --num 101 --note 'Regression, exact source and final receipt required. Same seed/body/native crop vector; native peak Adam1e-3 Muon4e-3 WSD; own-route SFT m8a16ckptON. Read native and SFT endpoints separately. Costs require five-minute idle. Estimated upper bound .25h GPU=N; worker cap900s. CPU prepare and resource forecast are not quality PASS. No automatic float deployment.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ezWo_native_route_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_weight_route.py --mode readback --max-wall-sec 900 --execute
