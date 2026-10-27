#!/usr/bin/env bash
# Preserve Stage11e actual84800/9. Measure all3 prefill controls, no tolerance edit.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode diagnose --max-wall-sec 900 --profile handoff/audit/oct27_independent/gguf_prefill_diagnosis_profile_v1.json --profile-sha256 29FCD57F86FF542E7102A0B22D4D922F8545146FB86CBA673313C0FB0C6E66EE)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_prefill_control.py --device cuda "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11fW_gpt2_prefill_shape_control --num 101 --note 'New controlled prefill1/32/512, same current worker/model/F32KV/context1024/batch512-capacity/threads. All4contexts x4positions x3partitions per device. Keep original Stage11e ERROR9/tolerance. Each decode computes its last head, so singleton extra-head cost is explicit. Diagnosis0 is not bulk correctness, generalKV/quality or resource adoption. No old Core6 execution, model writes/training/new300M/install/download.'
aggregate=0
for device in cuda cpu; do
    timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11fW_gpt2_prefill_shape_control --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_prefill_control.py --device "$device" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11fW_gpt2_prefill_shape_control --num 101 --note "Final device=$device diagnostic exit=$result. All positive and negative controls remain; singleton is self-consistency only. Separate resources require closed same-source/device singleton admission."
    if [[ "$result" != 0 ]]; then aggregate="$result"; fi
done
exit "$aggregate"
