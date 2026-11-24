#!/usr/bin/env bash
# Same packed payloads, new CPU1/worker1 and one logical CPU; not a CPU4 rerun.
# Forecast1-2h, hard parent9000s; GPU0; immutable prior payloads and results.
# Prerequisite check failure stops; no automatic retry of a partial child.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export PYTHONIOENCODING=utf-8
"$python_bin" -B -X utf8 -m scripts.diag_p014e_cpu_single_core check
result=$?
[[ "$result" == 0 ]] || exit "$result"
"$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6We_cpu_single_core --note 'CPU1/interop1/worker1, one pinned logical CPU, fresh anchors0/4. Same original rtol2e-5/atol2e-6 and IDs/stops. Read batch_report plus8 child reports; compare each same-CPU1 ABBA workload separately. Whole RSS is not weights+KV; no quality/40MiB/mobile claim. User158 authority ends17Nov17KST; new-work cutoff16:40. STOP=test_result/evidence/p014e_cpu1_native_v1_20261117_s1337/STOP. No install, download, original checkpoint write, protected data, Git mutation or deletion.'
timeout --signal=TERM --kill-after=90s 9300s "$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6We_cpu_single_core -- "$python_bin" -B -u -X utf8 -m scripts.diag_p014e_cpu_single_core actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6We_cpu_single_core --note "Actual shell exit=$result. Exit8 is a bounded HOLD, not a content PASS. Preserve every negative/partial report and child log; inspect model release and CUDA-uninitialized proof. No automatic restart."
exit "$result"
