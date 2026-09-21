#!/usr/bin/env bash
# P060B Stage0aWd: correct the Wc grouped-broadcast candidate to four dimensions
# by folding batch*kv_heads. Historical Wc 5-D UNAVAILABLE remains preserved.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWd_wsl_sdpa_gqa_backend \
  --note "P060B Stage0aWd: fold batch and KV heads into a 4-D grouped-broadcast candidate so EFFICIENT is tested without materialized KV repeat" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWd_wsl_sdpa_gqa_backend -- \
  "$python_bin" scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
