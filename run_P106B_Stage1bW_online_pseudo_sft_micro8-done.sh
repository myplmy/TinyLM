#!/usr/bin/env bash
# P106B Stage1bW: user-run full teacher plus trained P076 student micro8/accum16.
# About 0.5-0.75 h; ONLY 2 pseudo-label SFT updates and one isolated diagnostic checkpoint.
# Stage1aW candidate log/manifest and a fresh WSL smoke PASS are prerequisites.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
if [[ ! -f runs/ckpt/m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt || \
      -L runs/ckpt/m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt ]]; then
  printf '%s\n' '[STOP] trained P076 mean input checkpoint absent or linked' >&2
  exit 9
fi
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1bW_online_pseudo_sft_micro8.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1bW runlog already exists: %s; use a new stage suffix for retries.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1bW_online_pseudo_sft_micro8 --num 101 --note \
  'Prerequisite: Stage1aW 12/16 format PASS, fresh WSL smoke PASS, idle >=14GiB GPU. Student: trained P076 B3 mean, legacy tokenizer, micro8/accum16, activation checkpoint ON; teacher full GPU.'
"$python_bin" scripts/runlog.py --name P106B_Stage1bW_online_pseudo_sft_micro8 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_pseudo_sft.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1bW_online_pseudo_sft_micro8 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_pseudo_sft.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1bW_online_pseudo_sft_micro8 --num 101 --note \
  'Two updates at 128 conversation exposures/update. At least 8 unique auto-screened pseudo targets and sampled free >=2GiB are required. Pseudo labels are UNVERIFIED, not P106 ACCEPT. One tagged diagnostic checkpoint is saved only after all gates.'
"$python_bin" scripts/runlog.py --name P106B_Stage1bW_online_pseudo_sft_micro8 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_pseudo_sft.py --execute
