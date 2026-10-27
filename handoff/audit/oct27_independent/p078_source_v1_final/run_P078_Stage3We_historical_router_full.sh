#!/usr/bin/env bash
# FROZEN completed704 body; train49k prefix-head only, not new model300M.
# Require same new bridge prepare+cost+whole-budget actual0; no automatic shrink.
# TRAIN22528 labels, CPU head5epochs, DEV256 at1/3/5, TEST256 x4 policies once.
# Caps labels2h/head45min/TEST5h/readback15min; total8h upper plus cleanup.
# Current measured whole forecast and27Oct17KST authority gate every phase.
# This is route/IO/first-answer technical evidence, not model intelligence adoption.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--corpus-sha256 7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20 --holdout-sha256 C6B42D5A56E9608AF953A9E7614E28A74E16038A1CF6EAEDA303937E8639D6AC --profile handoff/audit/oct27_independent/p078_body_bridge_profile_v3.json --profile-sha256 682797192A047CEFB6BA2BFE115AED2F10D192997470C422F01362F9396927BB --authorization handoff/audit/oct27_independent/p078_router_authorization_v4.json --authorization-sha256 B703CDAE6D0D11062981F10F9A4426686C5BE26C7820928DEC4459D9E40E5170)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p078_prefix_router.py --mode labels --max-wall-sec 7200 "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3We_historical_router_full --num 066 --note 'Conditional full router only after Stage3Wd whole-budget readiness. Body and oldCP frozen; TRAIN-only labels andCPU prefix-head, DEV-only model selection, TEST four fixed quotas once. Every question/first answer remains raw. New router_head.pt is separate from original body. No semantic PASS or general intelligence adoption from this diagnostic; no new300M.'
for mode in labels fit evaluate readback; do
    case "$mode" in labels) cap=7200 ;; fit) cap=2700 ;; evaluate) cap=18000 ;; readback) cap=900 ;; esac
    timeout --signal=TERM --kill-after=20s "$((cap+60))s" "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3We_historical_router_full --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_prefix_router.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3We_historical_router_full --num 066 --note "Final phase=$mode exit=$result. Preserve failed/partial originals; no resume by waiving source/body/clock gates. Read unchanged split/actual answer/RSS/time and full raw recount."
    [[ "$result" == 0 ]] || exit "$result"
done
exit 0
