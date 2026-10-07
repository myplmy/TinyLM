#!/usr/bin/env bash
# User GPU0.50h/max30min; Gemma teacher-only off/on then on/off,16 requests.
# Card temp1/top-p0.95/top-k64,native thinking,external assistant/MTPnmax2.
# Asset gate first. Actual question/final/phase retained; no stdin/student/SFT.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6dW_gemma12b_role_mtp_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage6dW_gemma12b_role_mtp_pair --num 101 --note 'User GPU0.50h/max30min; teacher-onlyGemma off/on then on/off16 requests,one attempt each. Card1.0/0.95/64/native thinking; MTPexternal assistant/nmax2. Requires assets/newsmoke. Store actual question/final,raw reasoning,memory; format is not truth/Korean superiority.'
"$python_bin" scripts/runlog.py --name P106B_Stage6dW_gemma12b_role_mtp_pair --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_teacher_gate.py --mode role --execute
