#!/usr/bin/env bash
# Same frozen CPU models and CUDA CE; metadata wire-format recovery only.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/miniforge3/envs/tlm_torch/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
profile="handoff/audit/p102a_margin4gb_20261026/profile_v2.json"
profile_sha="5F589CE8DE9FF9ACC21DF526C5626700F24CEB2BDBBAB6A0496C4C07B40F9218"
source_sha="5BCE97511D0292B5B5B5F6FF9B30A07024667B4B28E24DE0BB3108159B372713"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p102a_logit_margin.py --profile "$profile" --profile-sha256 "$profile_sha"
fi
exec timeout --signal=TERM --kill-after=10s 960s "$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2hWb_cfg_margin_4gb --no-append -- "$python_bin" -B -X utf8 scripts/diag_p102a_logit_margin.py --profile "$profile" --profile-sha256 "$profile_sha" --source-sha256 "$source_sha" --execute
