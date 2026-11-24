#!/usr/bin/env bash
# Canonical content/EOT/margin diagnostic;completed14 states/FIT24 only.
# Freeze360 teacher-forcing forwards/24 VJP;no new answer generation/training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_margin check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage50Wb_margin_prepare_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_margin prepare
exit $?
