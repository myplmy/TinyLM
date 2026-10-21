#!/usr/bin/env bash
# Four independent four-pass704-update route arms, existing cost32 reused.
# Real four-cost preview forecasts8.62h total; reserve a separately approved
# window within40h. Worker limit4h, sampled peakreserved3086MiB in costs.
# Fresh exact authorization descriptor+SHA required; never reads stdin.
# Prerequisite preview HOLD stops all; independent train failures continue.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
name="P078_Stage2Wc_verified_route_full_${stamp}"
"$python_bin" -B -X utf8 scripts/runlog.py --name "$name" --num 066 --note 'Reuse four same-source cost32 reports through JSON verification adapter; original learning plans unchanged. Full704updates/arm, explicit-context22528TRAIN/512DEV, m8a16/ckptON/eager/MTPoff. Cost answers were wrong/repetitive; resource PASS is not intelligence PASS. Need fresh approved authority covering pending8.62h forecast plus actual margin. Final readback requires four actual completed checkpoints and answers.'
if [[ -z "${TL_P078_AUTHORIZATION:-}" || -z "${TL_P078_AUTHORIZATION_SHA256:-}" ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --name "$name" --num 066 --note 'HOLD8: supply TL_P078_AUTHORIZATION and TL_P078_AUTHORIZATION_SHA256 for a separately approved nonexpired execution window. No model started.'
    exit 8
fi
common=(--corpus HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus --corpus-sha256 7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20 --authorization "$TL_P078_AUTHORIZATION" --authorization-sha256 "$TL_P078_AUTHORIZATION_SHA256" --max-wall-sec 14400 --execute)
"$python_bin" -B -X utf8 scripts/runlog.py --name "$name" --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_route_protocol.py --mode budget-preview "${common[@]}"
preview_rc=$?
[[ "$preview_rc" == 0 ]] || exit "$preview_rc"
failed=0
for arm in uniform_r2 fixed_shuffle_r2 update_shuffle_r2 balanced_count; do
    "$python_bin" -B -X utf8 scripts/runlog.py --name "$name" --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_route_protocol.py --mode train --arm "$arm" "${common[@]}" || failed=1
done
"$python_bin" -B -X utf8 scripts/runlog.py --name "$name" --num 066 -- "$python_bin" -B -X utf8 scripts/diag_p078_route_protocol.py --mode readback "${common[@]}" || failed=1
exit "$failed"
