#!/usr/bin/env bash
# Independent AdaMuon FP32-V equations/state/cost only, no body training.
# One real8x1024 gradient; disposable copies only, common LR0.001, two orders.
# First-state plus5 steady steps, separate AdamW; no quality/300M adoption.
# Requires10GiB free;900s internal/960s outer. Any failure preserves evidence.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe
export TL_WANDB_AUTO=0
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
common=(--profile handoff/audit/oct27_independent/adamuon_cost_profile_v2.json --profile-sha256 82DABFECC3A80FDBA5411D959A935FC83551BB5D4E779431E49DF65439EDD5A6 --source-sha256 963096031CFF53A24DCDCA24A845D5D1354CCC0DD47B419D9ED42F7998D590BA --max-wall-sec 900)
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p005b_adamuon.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P005b_Stage16W_adamuon_gradient_cost --num 078 --note 'Sign-before-NS and full FP32 V, RMS0.2 candidate. Strict completed format Muon model is read-only. One FP32/MATH microbatch is NOT a full accum16 update. Disposable full parameter copies and common gradient; two cost orders with same AdamW groups. No body optimizer step, checkpoint write or quality score. Numeric8/error9/actual0 remain distinct.'
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P005b_Stage16W_adamuon_gradient_cost --num 078 -- "$python_bin" -B -X utf8 scripts/diag_p005b_adamuon.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P005b_Stage16W_adamuon_gradient_cost --num 078 --note "Final exit=$result. Read same-device oracle, actual state bytes, first/steady matrix and AdamW times, original core/cache SHA and owned cleanup. Zero is technical completion only; original Muon/NorMuon full-training negatives and default trainer are unchanged."
exit "$result"
