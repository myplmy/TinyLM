#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWb_wsl_sdpa_gqa_backend \
  --note "P060B Stage0aWb: Stage0aW excluded a practical on_default GQA path from its final candidate decision; this rerun reports dispatcher-selected and forced candidates separately" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWb_wsl_sdpa_gqa_backend -- \
  "$python_bin" scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
