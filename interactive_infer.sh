#!/usr/bin/env bash
# User-operated interactive tool. No run_ experiment prefix; never register in run_queue.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
exec "$python_bin" -B -X utf8 scripts/interactive_infer.py "$@"
