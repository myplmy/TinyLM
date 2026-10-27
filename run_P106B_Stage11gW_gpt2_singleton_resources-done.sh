#!/usr/bin/env bash
# Conditional same-function resources after all3 controlled prefill shapes.
# Singleton1 only; bulk32/512 numerical failures and prior ERROR9 remain.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode resources --max-wall-sec 1800 --profile handoff/audit/oct27_independent/gguf_singleton_resource_profile_v1.json --profile-sha256 FC173FBA36DB5D3BBBE47C55526B111A8028920213613943A7C9E3174E1E57FA)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_prefill_control.py --device cuda "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11gW_gpt2_singleton_resources --num 101 --note 'After closed controlled diagnosis74314/0 for both devices. Admit prefilling chunk1 only; same singleton function and extra head calls, not a bulk performance claim. Same35 source/build/asset/F32KV, full4contexts fixed32 warm1/timed3/observed3 plus4natural64. Native pick TTFT and IPC-wall arrival TTFT separate; exact native tensor/KV bytes NOT_MEASURED. Original bulk ERROR9 and32/512 negatives stay. No training/new300M/Core6 reevaluation/install/download.'
aggregate=0
for device in cuda cpu; do
    timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11gW_gpt2_singleton_resources --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_prefill_control.py --device "$device" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11gW_gpt2_singleton_resources --num 101 --note "Final singleton device=$device exit=$result. Full0/forecastHOLD8/error9 separate; no scope shrink or tolerance waiver. Independent next device runs after owned closure."
    if [[ "$result" != 0 ]]; then aggregate="$result"; fi
done
exit "$aggregate"
