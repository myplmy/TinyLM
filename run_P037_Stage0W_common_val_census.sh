#!/usr/bin/env bash
# P037 Stage0W: user-run read-only census of legacy ko-en 300M/600M caches.
# No HF download, cache write, model load or protected TinyDataset access.
# Estimate 0.5 h CPU alone/watch; exit 8 means real train/common-val overlap.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
for size in 300000000 600000000; do
  cache="data_cache/ko-en_$size"
  if [[ ! -f "$cache/meta.json" || ! -f "$cache/train.bin" || ! -f "$cache/val.bin" ]]; then
    printf '[STOP] exact legacy cache missing: %s\n' "$cache" >&2
    exit 9
  fi
done
"$python_bin" scripts/runlog.py --num 023 --name P037_Stage0W_common_val_census --note "P037 existing 300M/600M cache val identity, train order and document overlap; read-only."
"$python_bin" scripts/runlog.py --num 023 --name P037_Stage0W_common_val_census -- "$python_bin" -B -X utf8 scripts/diag_p037_common_val.py --self-test
"$python_bin" scripts/runlog.py --num 023 --name P037_Stage0W_common_val_census -- "$python_bin" -B -X utf8 scripts/diag_p037_common_val.py --check-only
"$python_bin" scripts/runlog.py --num 023 --name P037_Stage0W_common_val_census -- "$python_bin" -B -X utf8 scripts/diag_p037_common_val.py
