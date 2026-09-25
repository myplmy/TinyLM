#!/usr/bin/env bash
# P103A Stage1bW: user-run pinned M0 CUDA 2M fixed-window activation cache.
# Writes a new write-once runs/bench namespace (~7.8 GiB), never source cache.
# Estimate 2 h GPU alone/watch; exact first-window function must pass before build.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
target=runs/bench/p103a_stage1bw_m0_fixed2m
if [[ -e "$target" || -L "$target" ]]; then
  printf '[STOP] P103A write-once target exists: %s\n' "$target" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P103A_Stage1bW_m0_fixed2m_cache --note "P103A M0 12/4 pinned 2M fixed windows; exact FP32 and INT8-per64 files, no training."
"$python_bin" scripts/runlog.py --name P103A_Stage1bW_m0_fixed2m_cache -- "$python_bin" -B -X utf8 scripts/build_p103a_fixed2m.py --self-test
"$python_bin" scripts/runlog.py --name P103A_Stage1bW_m0_fixed2m_cache -- "$python_bin" -B -X utf8 scripts/build_p103a_fixed2m.py --check-only
"$python_bin" scripts/runlog.py --name P103A_Stage1bW_m0_fixed2m_cache -- "$python_bin" -B -X utf8 scripts/build_p103a_fixed2m.py --batch 2
