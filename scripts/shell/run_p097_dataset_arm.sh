#!/usr/bin/env bash
# P097 common cache preparation. The root launcher runs training directly through
# runlog so runlog can see ``train`` and update runs/registry.tsv.
set -u -o pipefail

if [[ "$#" -ne 2 ]]; then
    printf '%s\n' 'usage: run_p097_dataset_arm.sh DATA DOC_FILTER_0_OR_1' >&2
    exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
data_name="$1"
use_filter="$2"

"$python_bin" scripts/check_hf_runtime.py || exit $?

filter_args=()
if [[ "$use_filter" == "1" ]]; then
    filter_args+=(--doc-filter --doc-min-chars 50000)
elif [[ "$use_filter" != "0" ]]; then
    printf '[STOP] DOC_FILTER must be 0 or 1, got %s\n' "$use_filter" >&2
    exit 2
fi

exec "$python_bin" run100m.py prepare --data "$data_name" --tokens 600M \
  --pool-tokens 600M --exact-cache "${filter_args[@]}"
