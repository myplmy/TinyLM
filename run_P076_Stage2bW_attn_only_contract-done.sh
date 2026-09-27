#!/usr/bin/env bash
# P076 B3: user-run ag2 attention-only init gate, no training.
# Requires the pinned m100 dense parent and existing 600M ko-en val cache.
# Expected <=0.4 h on one GPU. Exit 8 is a valid negative init-band result.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
for input in runs/ckpt/m100_ko-en_300M_dense.pt data_cache/ko-en_600000000/meta.json data_cache/ko-en_600000000/val.bin; do
  if [[ ! -f "$input" || -L "$input" ]]; then
    printf '[STOP] P076 B3 exact input absent or linked: %s\n' "$input" >&2
    exit 9
  fi
done
"$python_bin" scripts/runlog.py --name P076_Stage2bW_attn_only_contract --note "Same ag2 student: default and explicit mean must be identical, MLP weights invariant, only attention norm-mean changes. Step0 is an init gate, not a quality ranking."
"$python_bin" scripts/runlog.py --name P076_Stage2bW_attn_only_contract -- "$python_bin" -B -X utf8 scripts/diag_p076_attn_only.py --check-only
"$python_bin" scripts/runlog.py --name P076_Stage2bW_attn_only_contract -- "$python_bin" -B -X utf8 scripts/diag_p076_attn_only.py
