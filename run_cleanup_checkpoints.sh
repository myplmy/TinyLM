#!/usr/bin/env bash
# Linux/WSL companion for run_cleanup_checkpoints.bat.
# Safety contract is unchanged: dry-run first, exact uppercase YES before deletion.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"

if [[ ! -f run100m.py ]]; then
    printf '%s\n' '[STOP] run this from the TinyLM working folder.' >&2
    exit 1
fi
python_bin="$(tinylm_python)" || exit $?

printf '%s\n' '=================== FROZEN PREVIEW AND CONFIRMATION ==================='
exec "$python_bin" scripts/cleanup_ckpt.py --interactive
