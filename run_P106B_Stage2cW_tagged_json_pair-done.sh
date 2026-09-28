#!/usr/bin/env bash
# P106B Stage2cW: user-run crossed tagged-vs-JSON teacher format gate.
# Pinned same 16 OASST2 pairs, model/sampler/context/seed, 32 requests total.
# Teacher-only RTX full-GPU, up to 42 min; no student train/ckpt/auto accept.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2cW_tagged_json_pair.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2cW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2cW_tagged_json_pair --num 101 --note \
  'Prerequisites: fresh user WSL smoke PASS, idle GPU/free >=8192MiB, exact v1-v4 source SHA. Crossed tagged vs JSON wire format on same 16 cases; v6 write-once raw reasoning/final. No student training.'
"$python_bin" scripts/runlog.py --name P106B_Stage2cW_tagged_json_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_tagged_pair.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2cW_tagged_json_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_tagged_pair.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2cW_tagged_json_pair --num 101 --note \
  'Gate: tagged final+canonical wrapper >=12/16; paired per-request completion tokens and wall report-only. A format PASS never validates answer truth, 50:50 bilingual quality, student SFT or broad corpus throughput.'
"$python_bin" scripts/runlog.py --name P106B_Stage2cW_tagged_json_pair --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_tagged_pair.py --execute
