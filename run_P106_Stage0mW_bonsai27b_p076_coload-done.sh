#!/usr/bin/env bash
# P106 Stage0mW: bounded, no-checkpoint co-load. Synthetic P076 one update only.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P106_Stage0mW_bonsai27b_p076_coload --num 098 --note \
  'User-approved narrow teacher+synthetic-student co-residency; FFN32 CPU, GDN fused, 1 eager optimizer update, no parent/cache/checkpoint/compile. Full P076 training NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106_Stage0mW_bonsai27b_p076_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_coload.py --self-test
"$python_bin" scripts/runlog.py --name P106_Stage0mW_bonsai27b_p076_coload --num 098 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106_coload.py --placement ffn32
