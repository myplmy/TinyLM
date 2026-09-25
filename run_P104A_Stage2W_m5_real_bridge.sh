#!/usr/bin/env bash
# P104A Stage2W real M5 WSL side. Run the Windows BAT on the same repo first.
# Same d14 dense checkpoint/cache/code SHA, full fixed val and one in-memory step.
# User-run GPU ~1.0 h alone/watch. No training checkpoint or cache is modified.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
win=runs/bench/p104a_m5_real_windows.json
wsl=runs/bench/p104a_m5_real_wsl.json
if [[ ! -f "$win" || -L "$win" || -e "$wsl" || -L "$wsl" ]]; then
  printf '[STOP] Windows real JSON is required and WSL output must be absent: %s %s\n' "$win" "$wsl" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P104A_Stage2W_m5_real_bridge --note "P104A identical real d14 checkpoint Windows/WSL fixed-val and one-step bridge; WSL follows Windows."
"$python_bin" scripts/runlog.py --name P104A_Stage2W_m5_real_bridge -- "$python_bin" -B -X utf8 scripts/check_m5_real_bridge.py --self-test
"$python_bin" scripts/runlog.py --name P104A_Stage2W_m5_real_bridge -- "$python_bin" -B -X utf8 scripts/diag_m5_real_bridge.py \
  --platform wsl --out "$wsl" --check-only
"$python_bin" scripts/runlog.py --name P104A_Stage2W_m5_real_bridge -- "$python_bin" -B -X utf8 scripts/diag_m5_real_bridge.py \
  --platform wsl --out "$wsl"
"$python_bin" scripts/runlog.py --name P104A_Stage2W_m5_real_bridge -- "$python_bin" -B -X utf8 scripts/check_m5_real_bridge.py \
  --win "$win" --wsl "$wsl" --max-ce-abs 0.01 --max-grad-rel 0.10
