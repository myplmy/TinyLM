#!/usr/bin/env bash
# P106B Stage2iWg: completed user low1 run, result101 section30; keep original command evidence.
# Former low1 used OASST1; this is not a duplicate source/backend gate.
# User-only GPU, at most 2h, full teacher + P076 micro8*accum16/ckpt-on.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWg_online1_public_low.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; do not delete HF output to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWg_online1_public_low --num 101 --note \
  'Low-first public Aya Dataset/OASST2 gate, not old OASST1 low1 repetition. New v17 write-once HF raw/canonical <=20MB shards, 128 fresh answers/1 optimizer, no checkpoint or quality claim. Ctrl+C is INTERRUPTED_USER/130; nvidia-smi timeout is telemetry tool failure/9, never healthy memory evidence. Model card does not guarantee low is faster; thinking sampler and ctx3072/max2048 are measured settings. Medium remains HOLD.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWg_online1_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_online_lifecycle.py
"$python_bin" scripts/runlog.py --name P106B_Stage2iWg_online1_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWg_online1_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort low --variant publiclow1
"$python_bin" scripts/runlog.py --name P106B_Stage2iWg_online1_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort low --variant publiclow1 --max-wall-sec 7200
