#!/usr/bin/env bash
# Maintenance only: default read-only preview; no model/GPU/experiment execution.
# Deletion requires --interactive (YES) or an explicitly approved manifest SHA.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/cleanup_isolated_ckpt.py "$@"
