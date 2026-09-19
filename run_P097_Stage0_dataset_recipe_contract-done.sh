#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --name P097_Stage0_dataset_recipe_contract \
  --note "P097 Stage0: exact token quotas, isolated recipe names, and repository-local HF cache; network/GPU/model 0" \
  || exit $?
"$python_bin" scripts/runlog.py --name P097_Stage0_dataset_recipe_contract -- \
  "$python_bin" scripts/check_hf_runtime.py || exit $?
exec "$python_bin" scripts/runlog.py --name P097_Stage0_dataset_recipe_contract -- \
  "$python_bin" scripts/test_dataset_recipes.py
