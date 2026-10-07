#!/usr/bin/env bash
# User GPU0.10h/max30min; old16 replies had tag errors. Opt-in start labels/newv2.
# Existing logs/outputs stay immutable; no stdin/download/teacher-owned JSON.
# New smoke first. Exit8 is gate-negative/HOLD,9 is tool failure.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage6dWb_gemma_start_label_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage6dWb_gemma_start_label_pair --num 101 --note 'User GPU0.10h/max30min; sameGemma/assistant/b11396/card1.0/.95/64/native1024-total3072-ctx8192/nmax2. New QUESTION-ANSWER-NOTE start labels,code wrapping; MTPoff/on then on/off16 first replies,no retry. Fields plus student context/mask are technical only; oldnegative preserved,new smoke first.'
"$python_bin" scripts/runlog.py --name P106B_Stage6dWb_gemma_start_label_pair --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_label_recovery.py --execute
