#!/usr/bin/env bash
# P106B Stage2gW: user-run tiny tagged-pilot student SFT wiring gate.
# Requires Stage2d v7 canonical train/val, pinned trained P076 mean parent.
# Student-only RTX GPU, micro8 x accum16 x 2 updates, ckpt-on; <1h estimate.
# Tiny repeat is not 300M/600M quality or verified teacher truth.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2gW_tagged_student_wiring.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2gW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2gW_tagged_student_wiring --num 101 --note \
  'Prerequisites: fresh WSL smoke PASS, idle RTX GPU, Stage2d v7 exact train/val SHA and P076 mean legacy parent. Teacher is offline; only final assistant text receives SFT loss.'
"$python_bin" scripts/runlog.py --name P106B_Stage2gW_tagged_student_wiring --num 101 -- \
  "$python_bin" -B -X utf8 scripts/train_p106b_tagged_pilot.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2gW_tagged_student_wiring --num 101 -- \
  "$python_bin" -B -X utf8 scripts/train_p106b_tagged_pilot.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2gW_tagged_student_wiring --num 101 --note \
  'Gate: two finite micro8xaccum16 updates, nonzero assistant supervised tokens, finite CE/gradient, new checkpoint+metadata only. Pseudo labels are unverified; base full-val, benchmarks and 300M/600M quality remain NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106B_Stage2gW_tagged_student_wiring --num 101 -- \
  "$python_bin" -B -X utf8 scripts/train_p106b_tagged_pilot.py --execute
