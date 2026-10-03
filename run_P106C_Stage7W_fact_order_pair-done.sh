#!/usr/bin/env bash
# P106C: same32 updates/draws, fixed versus half-reversed fact order.
# Authorized bounded diagnostic, not production SFT; max1800s, about4GiB VRAM.
# Dependent checks stop on failure; all messages retained by runlog; no input.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage7W_fact_order_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage7W_fact_order_pair --num 102 --note 'Fixed vs half-reversed order only; identical parent, gold, draws, micro8/accum4/seq256/ckpt-on.32 updates each;8/16/32 boundaries;1800s hard cap. Read paired target accuracy plus native loss, not individual50percent alone. Exit0 means comparison complete, not adoption.'
"$python_bin" scripts/runlog.py --name P106C_Stage7W_fact_order_pair --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_order_pair.py
"$python_bin" scripts/runlog.py --name P106C_Stage7W_fact_order_pair --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_order_pair.py --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage7W_fact_order_pair --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_order_pair.py --execute
