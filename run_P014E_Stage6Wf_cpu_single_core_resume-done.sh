#!/usr/bin/env bash
# Explicit cost replan, not automatic retry: carry completed CPU1 anchor0.
# Execute remaining7 once; child2700s, parent18000s, GPU0, original gates.
# Preserve v1 cost HOLD and timing gap; no install/download/Git/delete.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export PYTHONIOENCODING=utf-8
"$python_bin" -B -X utf8 -m scripts.diag_p014e_cpu_single_core_resume check
result=$?
[[ "$result" == 0 ]] || exit "$result"
"$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6Wf_cpu_single_core_resume --note 'User158 explicit2700s-child/18000s-parent cost replan. One completed CPU1 anchor is carried, seven remaining children are new. Preserve original cost HOLD/partial probe and timing gap. Same CPU1/worker1/affinity0, original rtol2e-5/atol2e-6,96 nonself logits/120 nonself generations. No CPU4 rerun, no smaller suite. New-work cutoff17Nov16:40KST, authority ends17KST. STOP=test_result/evidence/p014e_cpu1_resume_v2_20261117_s1337/STOP. Read both original and resumed reports; whole RSS is not weights+KV/40MiB or quality.'
timeout --signal=TERM --kill-after=90s 18300s "$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6Wf_cpu_single_core_resume -- "$python_bin" -B -u -X utf8 -m scripts.diag_p014e_cpu_single_core_resume actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 099 --name P014E_Stage6Wf_cpu_single_core_resume --note "Actual shell exit=$result. Exit8 remains HOLD; preserve every attempted child and its actual exit/resource cleanup. No automatic expansion/retry."
exit "$result"
