#!/usr/bin/env bash
# Derive total depth from actual serialized pre/middle/coda config fields.
# Failed v1/v2 sources/admissions/logs remain preserved; output is v3.
# CPU payload read;22 completed policy replays;no model forward or GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_cost_reuse check
fi
"$python_bin" -B -m scripts.diag_p108b_cost_reuse check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage47Wc_serialized_cost_accounting_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_cost_reuse actual
exit $?
