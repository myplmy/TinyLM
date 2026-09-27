#!/usr/bin/env bash
# P103A Stage1cWa: user-run sampled persisted cache readback plus tail gradient.
# Three fixed windows, no new cache or checkpoint, no optimizer update.
# Expected <=0.3 h GPU; full-2M whole-wall/quality remains a later gate.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/094_log_${stamp}_P103A_Stage1cWa_cache_tail_readback.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1cWa runlog already exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P103A_Stage1cWa_cache_tail_readback --num 094 --note \
  'Prerequisites: fresh user WSL smoke PASS, idle GPU, immutable P103A Stage1bW exact/INT8 2M cache and pinned M0 checkpoint. Read windows 0/976/1952 only; no cache rewrite, checkpoint or optimizer update.'
"$python_bin" scripts/runlog.py --name P103A_Stage1cWa_cache_tail_readback --num 094 -- \
  "$python_bin" -B -X utf8 scripts/diag_p103a_cache_tail_readback.py --self-test
"$python_bin" scripts/runlog.py --name P103A_Stage1cWa_cache_tail_readback --num 094 -- \
  "$python_bin" -B -X utf8 scripts/diag_p103a_cache_tail_readback.py --check-only
"$python_bin" scripts/runlog.py --name P103A_Stage1cWa_cache_tail_readback --num 094 --note \
  'Gate: persisted exact cache and uncached same-window logits/loss/all trainable gradients max-abs<=5e-5. INT8 error and sample wall/RSS are report-only. Three selected windows cannot prove full2M speed or language quality.'
"$python_bin" scripts/runlog.py --name P103A_Stage1cWa_cache_tail_readback --num 094 -- \
  "$python_bin" -B -X utf8 scripts/diag_p103a_cache_tail_readback.py --execute
