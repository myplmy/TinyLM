#!/usr/bin/env bash
# P106 Stage0nW: test more CPU FFN placement after FFN32 co-load had <0.5GiB headroom.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0nW_bonsai27b_ffn60_coload --num 098 --note \
  'User-approved bounded follow-up: full logical GPU with first60 FFN tensors on CPU, GDN fusion trace, then concurrent synthetic P076 one update; no parent/cache/checkpoint/compile.'
"$python_bin" scripts/runlog.py --name P106_Stage0nW_bonsai27b_ffn60_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0nW_bonsai27b_ffn60_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_vram_sample.py --gpu-layers all --fit-off --no-op-offload --ffn-cpu-first60 --verbosity 4 --require-fusion
"$python_bin" scripts/runlog.py --name P106_Stage0nW_bonsai27b_ffn60_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_coload.py --placement ffn60
