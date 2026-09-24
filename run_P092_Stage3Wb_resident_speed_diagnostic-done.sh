#!/usr/bin/env bash
# P092 Stage3Wb: diagnose existing 100M dense/static50/DST50 checkpoints.
# About 0.2 h, GPU inference only; no training or adoption decision.
# Stop on missing inputs; never overwrite a prior output or log.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage3Wb_resident_speed_diagnostic --note "P092: compare mask-inclusive held tensors, CUDA allocated delta, TTFT, decode tok/s. Historical training ms/step is a separate metric."
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage3Wb_resident_speed_diagnostic --   "$python_bin" -B -X utf8 scripts/diag_p092_resident_speed.py     --out runs/bench/p092_stage3wb_resident_speed.json --max-new 32 --reps 3
rc=$?
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "[FAIL] P092 Stage3Wb diagnostic rc=$rc; no 300M training follows" >&2
  exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage3Wb_resident_speed_diagnostic --note "Read runs/bench/p092_stage3wb_resident_speed.json plus this log. Diagnose and fix a measured cause before any one-seed 300M probe; the old 3-seed SH is -cancel history, not a DST-axis rejection."
