#!/usr/bin/env bash
# CPU frozen forward, CUDA logits only; no training, no model weight output.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/miniforge3/envs/tlm_torch/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
profile="handoff/audit/p102a_margin4gb_20261026/profile.json"
profile_sha="B98E6DF5FBDAFB393BEE1F53D6260ECD3AAA326215EC794A6C4095805A687A08"
source_sha="FAB4F1BFCE884B0D178C8CE512CCC56AAF073A04D4BD1CD01D072E440FEEFC9D"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p102a_logit_margin.py --profile "$profile" --profile-sha256 "$profile_sha"
fi
exec timeout --signal=TERM --kill-after=10s 960s "$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2hW_frozen_margin_4gb --no-append -- "$python_bin" -B -X utf8 scripts/diag_p102a_logit_margin.py --profile "$profile" --profile-sha256 "$profile_sha" --source-sha256 "$source_sha" --execute
