#!/usr/bin/env bash
# Closed local external HF resources, no training or content-based adoption.
# Strict loader initially uses CUDA even for CPU lanes; not CPU startup proof.
# Four models, fresh processes, FP32/eager, cached greedy128/512+32 tokens.
# Each lane1800s internal/1860s outer; independent failures continue.
# Available VRAM, entry10GiB and27Oct17KST deadline; no new packages/downloads.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/hf_resource_profile_v6.json --profile-sha256 B635A023E8C7E0CD735E0A704280473A4496FABCA444656835DAEB49A3A305F7 --source-sha256 752FB97868C54C199027304F2AAD0BA24DB7179B0E828869E1E66D4688AFB882 --max-wall-sec 1800)
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_hf_resources.py "${common[@]}" --model gemma270 --device cuda --check-only
fi
failed=0
codes=()
for device in cuda cpu; do
  for model in falcon90m gemma270 qwen06 gemma1b; do
    name="${model}_${device}"
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11cW_hf_"$name" --num 101 --note 'Closed Core6 model and exact assets, existing strict loader plus installed HF generate. CPU lane starts with CUDA validation then moves to CPU1, not CPU-only startup evidence. FP32/eager/cache-on, greedy, plain Base prompts, MTP/compile off. Unobserved throughput and streamer TTFT are separate; exact paired token/stop IDs required. No training, checkpoint writes or quality adoption.'
    timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11cW_hf_"$name" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_hf_resources.py "${common[@]}" --model "$model" --device "$device" --execute
    result=$?
    codes+=("${name}=$result")
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11cW_hf_"$name" --num 101 --note "Final lane exit=$result. Read original error, model/cache storage, allocator/RSS, observed vs plain generation and source/core closure. Zero is a technical lane completion only."
    [[ "$result" == 0 ]] || failed=9
  done
done
"$python_bin" -B -X utf8 -c 'import json,pathlib,sys; p=pathlib.Path("test_result/evidence/p106b_hf_resources_v1_20261027/launcher_receipt.json"); p.parent.mkdir(parents=True,exist_ok=True); d=dict(schema="HF_RESOURCE_LAUNCHER_CHILD_CODES_V1",child_codes=dict(x.split("=",1) for x in sys.argv[2:]),launcher_decided_returncode=int(sys.argv[1]),actual_os_parent_exit_is_separate=True); p.open("x",encoding="utf-8").write(json.dumps(d,indent=2)+chr(10)); print(json.dumps(d))' "$failed" "${codes[@]}"
summary_result=$?
[[ "$summary_result" == 0 ]] || failed=9
exit "$failed"
