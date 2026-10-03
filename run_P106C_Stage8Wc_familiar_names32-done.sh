#!/usr/bin/env bash
# P106C names: two bounded diagnostic arms, not production SFT.
# Same parent geometry, micro8/accum4/seq256/ckpt-on; max1800s, about4GiB VRAM.
# Dependent checks fail closed; no input; preserve old output/log.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage8Wc_familiar_names32.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing log: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage8Wc_familiar_names32 --num 102 --note 'Bounded names diagnostic; no teacher, no production SFT. Same facts/gold and explicit source SHA; report x and target tokens separately.1800s cap; exit0 is comparison completion, not adoption. Native CE and actual paired answers required.'
"$python_bin" scripts/runlog.py --name P106C_Stage8Wc_familiar_names32 --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_learning_controls.py
"$python_bin" scripts/runlog.py --name P106C_Stage8Wc_familiar_names32 --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_learning_controls.py --mode names --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage8Wc_familiar_names32 --num 102 -- "$python_bin" -B -X utf8 scripts/diag_p106c_learning_controls.py --mode names --execute
