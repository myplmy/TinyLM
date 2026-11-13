#!/usr/bin/env bash
# Prefix-only learned router on an already completed frozen balanced704 body.
# CPU prepared fresh512 holdout must exist; actual cost8 gates all further work.
# Unmeasured total; current estimate1.5h is provisional, hard family40h.
# Body training is not repeated. Dependency failure stops this pipeline only.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
name="P078_Stage3Wc_prefix_router_full_${stamp}"
"$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wc_prefix_router_full_"$stamp" --num 066 --note 'V2 scientific router: require prepared fresh512 holdout and closed balanced_count704 body, exact source/corpus/holdout/body/current authority. Current1.5h estimate is UNMEASURED; cost8 plus fresh pending-budget gate owns admission within40h. Body frozen, labels TRAIN only, DEV chooses head, TEST four fixed policies once. Read actual answers; CE is not truth. No R1 fallback or automatic adoption.'
if [[ -z "${TL_P078_ROUTER_AUTHORIZATION:-}" || -z "${TL_P078_ROUTER_AUTHORIZATION_SHA256:-}" || -z "${TL_P078_ROUTER_HOLDOUT_SHA256:-}" ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wc_prefix_router_full_"$stamp" --num 066 --note 'HOLD8: separately approved router authority+SHA and exact CPU holdout report SHA required. Balanced body704 is closed; router labels/head/evaluation are NOT_RUN. No GPU or model started.'
    exit 8
fi
common=(--corpus-sha256 7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20 --holdout-sha256 "$TL_P078_ROUTER_HOLDOUT_SHA256" --authorization "$TL_P078_ROUTER_AUTHORIZATION" --authorization-sha256 "$TL_P078_ROUTER_AUTHORIZATION_SHA256" --execute)
for mode in cost budget labels fit evaluate readback; do
    case "$mode" in
        labels) cap=21600 ;;
        fit) cap=7200 ;;
        evaluate) cap=14400 ;;
        *) cap=1200 ;;
    esac
    "$python_bin" -B -X utf8 scripts/runlog.py --name P078_Stage3Wc_prefix_router_full_"$stamp" --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_prefix_router.py --mode "$mode" --max-wall-sec "$cap" "${common[@]}"
    result=$?
    [[ "$result" == 0 ]] || exit "$result"
done
