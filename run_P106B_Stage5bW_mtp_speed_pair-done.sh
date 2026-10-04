#!/usr/bin/env bash
# P106B Teacher-only MTP off/on ABBA,16 requests; hard1h.
# Current xhigh sampler/budget; fixed benign KO/EN questions, no student.
# All calls are logged; dependent preflight fails closed; never read stdin.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage5bW_mtp_speed_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage5bW_mtp_speed_pair --num 101 --note 'Teacher-only MTP off/on ABBA,16 requests; hard1h. Same MTP GGUF, spec-draft-n-max2, LoRA scale1.0. Read real question/answer packet, normalized decode plus request wall, sampled GPU/RSS. Refusal labels offline; no training/default update. No input wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage5bW_mtp_speed_pair --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mtp_teacher.py
"$python_bin" scripts/runlog.py --name P106B_Stage5bW_mtp_speed_pair --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mtp_teacher.py --mode mtp --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage5bW_mtp_speed_pair --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mtp_teacher.py --mode mtp --execute
