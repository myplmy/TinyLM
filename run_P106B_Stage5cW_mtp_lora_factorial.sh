#!/usr/bin/env bash
# P106B Teacher-only MTP/LoRA2x2,32 requests; hard2h.
# User choice C: HOLD until offline observed educational-refusal evidence exists.
# Current xhigh sampler/budget; fixed benign KO/EN questions, no student.
# All calls are logged; dependent preflight fails closed; never read stdin.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage5cW_mtp_lora_factorial.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage5cW_mtp_lora_factorial --num 101 --note 'User choice C: HOLD until reviewed allowed educational refusal evidence is present in lora_trigger.json. Teacher-only MTP/LoRA2x2,32 requests; hard2h. Same MTP GGUF, spec-draft-n-max2, LoRA scale1.0. Read question/answer packet, decode and request wall, GPU/RSS. No input wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage5cW_mtp_lora_factorial --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mtp_teacher.py
"$python_bin" scripts/runlog.py --name P106B_Stage5cW_mtp_lora_factorial --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mtp_teacher.py --mode lora --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage5cW_mtp_lora_factorial --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mtp_teacher.py --mode lora --execute
