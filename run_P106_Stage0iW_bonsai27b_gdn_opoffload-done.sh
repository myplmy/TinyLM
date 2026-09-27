#!/usr/bin/env bash
# P106 Stage0iW: isolate op-offload at GPU40, then check GPU48.
# Same published PTQ1_0, Prism build, prompt, context, tokens and NVML sampler.
set -uo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0iW_bonsai27b_gdn_opoffload --num 098 --note \
  'A GPU40 fit-off/default op-offload; B GPU40 fit-off/no-op-offload; C GPU48 fit-off/no-op-offload. Same ctx512/output64. Exit8 is valid fusion-negative, exit9 execution failure.'
"$python_bin" scripts/runlog.py --name P106_Stage0iW_bonsai27b_gdn_opoffload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test || exit 9

rc_a=0
"$python_bin" scripts/runlog.py --name P106_Stage0iW_bonsai27b_gdn_opoffload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 40 --fit-off || rc_a=$?
rc_b=0
"$python_bin" scripts/runlog.py --name P106_Stage0iW_bonsai27b_gdn_opoffload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 40 --fit-off --no-op-offload --require-fusion || rc_b=$?
rc_c=0
"$python_bin" scripts/runlog.py --name P106_Stage0iW_bonsai27b_gdn_opoffload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers 48 --fit-off --no-op-offload --require-fusion || rc_c=$?

printf '[P106 Stage0iW] rc A=%s B=%s C=%s\n' "$rc_a" "$rc_b" "$rc_c"
if [[ "$rc_a" -ne 0 || ( "$rc_b" -ne 0 && "$rc_b" -ne 8 ) || ( "$rc_c" -ne 0 && "$rc_c" -ne 8 ) ]]; then
  echo '[FAIL] one runtime arm did not execute cleanly; do not infer fusion economics'
  exit 9
fi
if [[ "$rc_b" -eq 8 || "$rc_c" -eq 8 ]]; then
  echo '[GATE NEGATIVE] no-op-offload did not restore both GDN fused paths in all candidate arms'
  exit 8
fi
echo '[COLLECTED] inspect numeric and fusion rows; do not adopt from synthetic prompt alone'
