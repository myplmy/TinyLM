#!/usr/bin/env bash
# Frozen completed models only; no training, checkpoint write or source cleanup.
# Each model/device has a fresh process and a1800s internal/1860s external cap.
# Authority: current user96,27Oct17KST, available VRAM; old4GB cap removed.
# Independent failures continue; final9 retains any failed lane.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/resource_profile_v2.json --profile-sha256 C53E523BC53A2298A166FF10AEDC4EEFB48E1F8C9C280FE03DD283A66FB962B7 --source-sha256 F9BD28AFB3C7D6FAD88C497CE0C8C4453D5D82913438EB6439CEEFBBCADF16FC --max-wall-sec 1800)
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_resource_matrix.py "${common[@]}" --model format_muon --device cuda --check-only
fi
failed=0
for device in cuda cpu; do
  for model in native595-q native595-f new595-broad-f format_muon format_normuon; do
    name="${model//-/_}_${device}"
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11aW_resource_"$name" --num 101 --note 'Frozen resource observation: actual picked-token TTFT, fixed32 generated tokens,128/512 prompts, warmup1 measured3. Natural EOS/EOT answers are separate. Physical storage, KV, process RSS and GPU allocator peaks are distinct. No training or quality adoption.'
    timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11aW_resource_"$name" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_resource_matrix.py "${common[@]}" --model "$model" --device "$device" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11aW_resource_"$name" --num 101 --note "Final lane exit=$result; inspect immutable report and actual parent exit. Zero is a resource-lane completion only; not a content PASS or full matrix closure."
    [[ "$result" == 0 ]] || failed=9
  done
done
exit "$failed"
