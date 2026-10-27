#!/usr/bin/env bash
# New payloads only: original-scale body, unchanged or existing-TWN embedding.
# CPU1, frozen completed model; no GPU, training, original checkpoint writes.
# Exit0 is a technical suite, exit8 a budget HOLD, exit9 an error.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/packed_deploy_profile_v3.json --profile-sha256 A68A5EE83A7141E34923EFDA99D47A33F09A6EC7192F526EEFACD10B0F04F401)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_packed_deploy.py --mode prepare --max-wall-sec 60 "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wb_original_scale_cpu_deploy --num 099 --note 'CPU1 only. Completed Native595-Q, no body training/new300M/original checkpoint writes. Original g128 scales and existing five-trit codec. FP32 embedding and existing TWN embedding are separate variants. Full fixed16 timing and natural32 raw answers are technical evidence, not quality adoption. Shared host load is disclosed. New model payloads remain outside Git.'
for mode in prepare export baseline-cpu deploy-cpu; do
    case "$mode" in prepare) cap=60 ;; export) cap=600 ;; baseline-cpu) cap=900 ;; deploy-cpu) cap=1200 ;; esac
    timeout --signal=TERM --kill-after=20s "$((cap+60))s" "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wb_original_scale_cpu_deploy --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_packed_deploy.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wb_original_scale_cpu_deploy --num 099 --note "Final phase=$mode exit=$result. Read exact report: technical completion, budget HOLD8, or ERROR9. No missing phase is a PASS. Previous originals and negative evidence remain unchanged."
    [[ "$result" == 0 ]] || exit "$result"
done
exit 0
