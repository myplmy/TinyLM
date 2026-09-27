#!/usr/bin/env bash
# P106 Stage0lW: recover Stage0i's invalid verbosity-3 fusion classification.
# Same A/B/C placement, but verbosity 4 exposes GDN enabled/disabled evidence.
set -uo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0lW_bonsai27b_gdn_trace4 --num 098 --note \
  'Trace4 repair: A GPU40 fit-off/op-on, B GPU40 fit-off/op-off, C GPU48 fit-off/op-off. Same exact model/ctx512/output64; B/C require explicit GDN AR+chunked enabled lines.'
"$python_bin" scripts/runlog.py --name P106_Stage0lW_bonsai27b_gdn_trace4 --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test || exit 9
rc_a=0
"$python_bin" scripts/runlog.py --name P106_Stage0lW_bonsai27b_gdn_trace4 --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 40 --fit-off --verbosity 4 || rc_a=$?
rc_b=0
"$python_bin" scripts/runlog.py --name P106_Stage0lW_bonsai27b_gdn_trace4 --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 40 --fit-off --no-op-offload --verbosity 4 --require-fusion || rc_b=$?
rc_c=0
"$python_bin" scripts/runlog.py --name P106_Stage0lW_bonsai27b_gdn_trace4 --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 48 --fit-off --no-op-offload --verbosity 4 --require-fusion || rc_c=$?
printf '[P106 Stage0lW] rc A=%s B=%s C=%s\n' "$rc_a" "$rc_b" "$rc_c"
if [[ "$rc_a" -ne 0 || ( "$rc_b" -ne 0 && "$rc_b" -ne 8 ) || ( "$rc_c" -ne 0 && "$rc_c" -ne 8 ) ]]; then
  echo '[FAIL] CLI or sampler error; no fusion conclusion'
  exit 9
fi
if [[ "$rc_b" -eq 8 || "$rc_c" -eq 8 ]]; then
  echo '[GATE NEGATIVE] trace4 confirms missing fused AR/chunked path in at least one candidate'
  exit 8
fi
echo '[COLLECTED] explicit trace4 GDN enable status; speed and concurrent training remain separate'
