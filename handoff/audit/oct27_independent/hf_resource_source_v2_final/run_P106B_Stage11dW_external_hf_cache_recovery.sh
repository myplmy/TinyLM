#!/usr/bin/env bash
# Closed local external HF resources, no training or content-based adoption.
# Strict loader initially uses CUDA even for CPU lanes; not CPU startup proof.
# First a real shared runtime probe, then four models in fresh processes.
# FP32/eager, cached greedy128/512+32 tokens; no HF imports during hashing.
# Each lane1800s internal/1860s outer; independent failures continue.
# Available VRAM, entry10GiB and27Oct17KST deadline; no new packages/downloads.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
common=(--profile handoff/audit/oct27_independent/hf_resource_recovery_profile_v1.json --profile-sha256 415CAAA18B9EFAECDFF58EDEB0D4F669579EE12EEF4CF1D77C50EE721A076ABC --source-sha256 C8ACB350B74C3C6042507EA8D1DA6CEF7CF7EFA02D12D445A7AC766F1669054A --max-wall-sec 1800)
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_hf_resources.py "${common[@]}" --model gemma270 --device cuda --mode probe --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_runtime_probe --num 101 --note 'Recovery: package-source hashes use metadata paths without importing HF. Existing cache policy must initialize first. A real Gemma270 CUDA probe gates the eight independent full resource lanes. Probe completion is technical readiness, never intelligence.'
timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_runtime_probe --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_hf_resources.py "${common[@]}" --model gemma270 --device cuda --mode probe --execute
probe_result=$?
if [[ "$probe_result" != 0 ]]; then
  "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_runtime_probe --num 101 --note "Shared runtime probe exit=$probe_result; all eight matrix lanes NOT_RUN. Preserve the original failure; no automatic retry or quality conclusion."
  exit "$probe_result"
fi
failed=0
codes=()
for device in cuda cpu; do
  for model in falcon90m gemma270 qwen06 gemma1b; do
    name="${model}_${device}"
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_"$name" --num 101 --note 'Closed Core6 model and exact assets, existing strict loader plus installed HF generate. CPU lane starts with CUDA validation then moves to CPU1, not CPU-only startup evidence. FP32/eager/cache-on, greedy, plain Base prompts, MTP/compile off. Unobserved throughput and streamer TTFT are separate; exact paired token/stop IDs required. No training, checkpoint writes or quality adoption.'
    timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_"$name" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_hf_resources.py "${common[@]}" --model "$model" --device "$device" --mode full --execute
    result=$?
    codes+=("${name}=$result")
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11dW_hf_"$name" --num 101 --note "Final lane exit=$result. Read original error, model/cache storage, allocator/RSS, observed vs plain generation and source/core closure. Zero is a technical lane completion only."
    [[ "$result" == 0 ]] || failed=9
  done
done
"$python_bin" -B -X utf8 -c 'import json,pathlib,sys; p=pathlib.Path("test_result/evidence/p106b_hf_resources_v2_20261027/launcher_receipt.json"); p.parent.mkdir(parents=True,exist_ok=True); d=dict(schema="HF_RESOURCE_LAUNCHER_CHILD_CODES_V1",child_codes=dict(x.split("=",1) for x in sys.argv[2:]),launcher_decided_returncode=int(sys.argv[1]),actual_os_parent_exit_is_separate=True); p.open("x",encoding="utf-8").write(json.dumps(d,indent=2)+chr(10)); print(json.dumps(d))' "$failed" "${codes[@]}"
summary_result=$?
[[ "$summary_result" == 0 ]] || failed=9
exit "$failed"
