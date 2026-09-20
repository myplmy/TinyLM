#!/usr/bin/env bash
# Recheck the corrected WSL-native PATH, exact-cache validator, iterator close
# propagation, and MADLAD direct-shard routing. Network/GPU/model execution: 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 090 --name P097_Stage0b_dataset_recipe_contract   --note "P097 Stage0b: WSL native PATH, exact cache integrity, iterator close, and MADLAD direct-shard contracts; network/GPU/model 0"   || exit $?
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage0b_dataset_recipe_contract --   "$python_bin" scripts/check_hf_runtime.py || exit $?
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage0b_dataset_recipe_contract --   "$python_bin" scripts/test_tinylm_env.py || exit $?
exec "$python_bin" scripts/runlog.py --num 090 --name P097_Stage0b_dataset_recipe_contract --   "$python_bin" scripts/test_dataset_recipes.py
