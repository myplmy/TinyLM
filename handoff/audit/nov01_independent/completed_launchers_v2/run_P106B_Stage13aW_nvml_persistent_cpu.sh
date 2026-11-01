#!/usr/bin/env bash
# Persistent NVML IPC fixtures only; never opens the real NVML/GPU library.
# Retains inherited three consecutive failures and a three-second query cap.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13aW_nvml_persistent_cpu -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_nvml_probe
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13aW_nvml_persistent_cpu --note "actual_exit=$result; CPU8 fixtures, bounded owned-child timeout/closure, inherited three-consecutive-failure policy. No real NVML/model/GPU/install/download. This is not adoption or a long-run reliability claim."
exit "$result"
