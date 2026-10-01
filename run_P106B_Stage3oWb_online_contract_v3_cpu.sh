#!/usr/bin/env bash
# P106B_Stage3oWb_online_contract_v3_cpu: expected 0.10h. CPU-only shared budget, known/UNKNOWN slots, warning modes and report-domain regressions; no models.
# New stage/version only; originals preserved; every prerequisite failure stops this launcher.
# No interactive input. CPU/static success does not imply new teacher/student quality.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3oWb_online_contract_v3_cpu.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 --note 'CPU-only shared budget, known/UNKNOWN slots, warning modes and report-domain regressions; no models. Read raw answers and report domains separately. Admission is not truth; no stdin wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_output_contract.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_review_packet
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_request_budget.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_saved_answers.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oWb_online_contract_v3_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_contract_gate.py --self-test
