#!/usr/bin/env bash
# P037 Stage0Wb: user-run CPU-only isolated 300M common-validation cache builder.
# Budget: about 1 h and at least 2 GiB free; no GPU, download, model, or training.
# This changes only a NEW data_cache namespace. The Codex preparation turn must
# not execute this launcher or the real-cache --check-only/default modes.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
"$python_bin" scripts/runlog.py --name P037_Stage0Wb_common_val_300M_builder --num 023 --note \
  'Build isolated ko-en-commonval-v1 300M cache from existing 300M train and pinned 600M val; exclude exact overlapping documents. CPU/data gate only. No SFT training or quality claim.'
"$python_bin" scripts/runlog.py --name P037_Stage0Wb_common_val_300M_builder --num 023 -- \
  "$python_bin" -B -X utf8 scripts/build_p037_common_val.py --self-test
"$python_bin" scripts/runlog.py --name P037_Stage0Wb_common_val_300M_builder --num 023 -- \
  "$python_bin" -B -X utf8 scripts/build_p037_common_val.py --check-only
"$python_bin" scripts/runlog.py --name P037_Stage0Wb_common_val_300M_builder --num 023 -- \
  "$python_bin" -B -X utf8 scripts/build_p037_common_val.py
printf '%s\n' '[COLLECTED] P037 isolated 300M cache written and document-level checks passed; SFT/multiturn learning remains NOT_RUN.'
