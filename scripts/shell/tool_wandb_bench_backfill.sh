#!/usr/bin/env bash
# Zero arguments prints the bounded P097 benchmark plan; --push performs it.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

exec "$python_bin" scripts/wandb_bench_backfill.py "$@"
