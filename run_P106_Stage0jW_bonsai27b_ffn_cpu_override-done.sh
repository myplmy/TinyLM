#!/usr/bin/env bash
# P106 Stage0jW: verified GGUF FFN tensor names, first32 FFN CPU placement.
# Four bounded teacher-alone arms separate fit/op-offload and tensor placement.
set -uo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 --note \
  'A full fit-off/default op-offload; B full fit-off/no-op-offload; C B plus first32 FFN CPU tensor override; D A plus override. Same model SHA/ctx512/output64, each120s. Tensor names 96/1,871,708,160B from exact GGUF metadata.'
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test || exit 9

rc_a=0
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all --fit-off || rc_a=$?
rc_b=0
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all --fit-off --no-op-offload || rc_b=$?
rc_c=0
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all --fit-off --no-op-offload --ffn-cpu-first32 || rc_c=$?
rc_d=0
"$python_bin" scripts/runlog.py --name P106_Stage0jW_bonsai27b_ffn_cpu_override --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all --fit-off --ffn-cpu-first32 || rc_d=$?
printf '[P106 Stage0jW] rc A=%s B=%s C=%s D=%s\n' "$rc_a" "$rc_b" "$rc_c" "$rc_d"
if [[ "$rc_a" -ne 0 || "$rc_b" -ne 0 || "$rc_c" -ne 0 || "$rc_d" -ne 0 ]]; then
  echo '[FAIL] one arm failed to execute; preserve all rows and do not adopt tensor override'
  exit 9
fi
echo '[COLLECTED] compare actual GPU memory, CPU/GPU placement, fusion state and tok/s; synthetic arithmetic is not teacher quality.'
