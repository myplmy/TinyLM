#!/usr/bin/env bash
# Reusable user-operated GPU tool; never register in experiments.tsv/run_queue.
set -euo pipefail
cd -- "$(dirname -- "$0")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
exec "$python_bin" -B -X utf8 scripts/interactive_research_infer.py "$@"
