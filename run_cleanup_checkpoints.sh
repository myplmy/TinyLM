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

printf '%s\n' '============================== DRY RUN ====================================='
"$python_bin" scripts/cleanup_ckpt.py || {
    printf '%s\n' '[STOP] could not build the deletion plan.' >&2
    exit 1
}

printf '%s\n' '============================================================================='
printf '%s\n' 'The list above WOULD be deleted. Nothing has been removed yet.'
printf '%s\n' 'Type YES in capitals to delete; anything else cancels.'
printf '%s\n' '============================================================================='
read -r -p 'delete these files? ' tl_ok
if [[ "$tl_ok" != "YES" ]]; then
    printf '%s\n' '[cancel] nothing was deleted.'
    exit 0
fi

printf '%s\n' '============================== DELETING ===================================='
"$python_bin" scripts/cleanup_ckpt.py --yes || {
    printf '%s\n' '[WARN] some files could not be deleted; inspect the list above.' >&2
    exit 1
}
printf '%s\n' '[done] cleanup finished.'
