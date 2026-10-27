#!/usr/bin/env bash
# Serial GPU only after the owned P078 parent actually closes and idle admission.
# CPU-made Q scales and same-device reference isolate codec from quantizer drift.
# FP32/TWN embedding results, raw answers, storage, peak, KV and cleanup separate.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/packed_deploy_profile_v3.json --profile-sha256 A68A5EE83A7141E34923EFDA99D47A33F09A6EC7192F526EEFACD10B0F04F401)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_packed_deploy.py --mode prepare --max-wall-sec 60 "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wc_original_scale_cuda_deploy --num 099 --note 'GPU2-thread FP32 MATH/cache-on, no MTP/compile/training/new300M. Require actual P078 closure and idle GPU. Baseline has an independently copied exact Q body and CPU-made scales; packed worker only loads new payload/oracle files. Weight storage and retained reference embedding differ from total startup/RSS/VRAM. Tiled unpack may be slower. No quality or40MiB adoption from file bytes.'
for mode in baseline-cuda deploy-cuda readback; do
    case "$mode" in baseline-cuda) cap=900 ;; deploy-cuda) cap=1200 ;; readback) cap=120 ;; esac
    timeout --signal=TERM --kill-after=20s "$((cap+60))s" "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wc_original_scale_cuda_deploy --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_packed_deploy.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wc_original_scale_cuda_deploy --num 099 --note "Final phase=$mode exit=$result. Exact profile/source and complete same-device oracle/ID/stop/cleanup are required. HOLD8 and NOT_RUN remain separate from a technical completion. No language-quality adoption."
    [[ "$result" == 0 ]] || exit "$result"
done
exit 0
