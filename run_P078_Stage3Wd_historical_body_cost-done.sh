#!/usr/bin/env bash
# Existing balanced704 body, no body training or source-guard bypass.
# New explicit historical/current bridge; CPU prepare -> actualGPU cost -> budget.
# Full-prefix896+forced128 and R1/2/3, real64-label IO, full pending DEV/TEST.
# Caps600/1200/600s plus parent reserve; all phases gated by user27Oct17KST.
# Dependencies stop this pipeline; no R1 fallback, crop, or quality adoption.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--corpus-sha256 7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20 --holdout-sha256 C6B42D5A56E9608AF953A9E7614E28A74E16038A1CF6EAEDA303937E8639D6AC --profile handoff/audit/oct27_independent/p078_body_bridge_profile_v3.json --profile-sha256 682797192A047CEFB6BA2BFE115AED2F10D192997470C422F01362F9396927BB --authorization handoff/audit/oct27_independent/p078_router_authorization_v4.json --authorization-sha256 B703CDAE6D0D11062981F10F9A4426686C5BE26C7820928DEC4459D9E40E5170)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p078_prefix_router.py --mode cost --max-wall-sec 1200 "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wd_historical_body_cost --num 066 --note 'New explicit historical704 body bridge: old report/activity/header remain historical, current source/core are independently checked. No body optimizer or300M. CPU24 reference cases and full AST guard equivalence; current profile/authority required. Real forced896+128 R1/2/3 and64 TRAIN-label IO gate all unchanged labels/head/DEV/TEST within27Oct17KST. Read actual errors and final codes; no small-sample intelligence adoption.'
for mode in prepare cost budget; do
    case "$mode" in cost) cap=1200 ;; *) cap=600 ;; esac
    timeout --signal=TERM --kill-after=20s "$((cap+60))s" "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wd_historical_body_cost --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_prefix_router.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wd_historical_body_cost --num 066 --note "Final phase=$mode exit=$result. Full pending budget includes label IO/readback/metadata/cleanup; failure or HOLD stops before full router."
    [[ "$result" == 0 ]] || exit "$result"
done
exit 0
