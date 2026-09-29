#!/usr/bin/env bash
# P106B Stage3fWb: user-run one-slot A2 producer/consumer plus B2 and C-reader.
# Expected about 1-1.5 GPU hours; hard wall <=2 hours. Exit0 technical only,
# exit8 negative/HOLD, exit9 tool failure, exit130 interrupt.
# No verified-answer, model-quality, 4-epoch, or 300M training claim.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3fWb_integrated_a2_one_slot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; do not remove HF output to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3fWb_integrated_a2_one_slot --num 101 --note \
  'One-slot A2 overlap integration: v27 functional PASS plus B2/B4 format and C4 safety are prerequisites. Teacher emits labeled QUESTION/ANSWER_1/ANSWER_2 with pinned thinking sampler and at most 3 recorded attempts per concept; code owns JSON/ChatML. C reader epoch1 gives64 replay rows and teacher gives64 fresh public rows. Require exact128 rows, 16 micro8, one optimizer, actual overlap, finite loss/grad and healthy VRAM/GDN; output v28 is write-once. A1 two-slot speed is negative and not required. This is technical wiring only: checkpoint0, answer quality and formal SFT NOT_RUN. User GPU only, hard<=2h.'
"$python_bin" scripts/runlog.py --name P106B_Stage3fWb_integrated_a2_one_slot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3fWb_integrated_a2_one_slot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_a2_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3fWb_integrated_a2_one_slot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_a2_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3fWb_integrated_a2_one_slot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_a2_gate.py --execute
