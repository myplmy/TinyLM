#!/usr/bin/env bash
# Actual old-model cost only; optimizer0/CP0, no dataset training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
common=(--profile handoff/audit/oct27_independent/p107_hybrid_profile_v1.json --profile-sha256 9EF350FC8D5B3814E9AA97C399FC6EE943F2274F0DFD9A74A2A0172CB31EB63C --max-wall-sec 900)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p107_hybrid_mntp.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage1W_mntp_forward_backward_cost --num 107 --note "Same Native595-Q, checkpointON/BF16/R1/noKD/noMTP; four mirrored conditions default/doc-causal/MNTP/hybrid8+8, same131072input per virtual update. Uniform15percent reserved13 corruption; separate whole-update target means. No optimizer/new300M/corpus/CP writes/quality. Internal900s, external1020+kill20s; closure must fit before27Oct17KST."
timeout --signal=TERM --kill-after=20s 1020s "$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage1W_mntp_forward_backward_cost --num 107 -- "$python_bin" -B -X utf8 scripts/diag_p107_hybrid_mntp.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P107_Stage1W_mntp_forward_backward_cost --num 107 --note "Final actual_exit=$result; full technical0/budgetHOLD8/error9/external timeout124-or137 distinct. Missing final report or nonzero cleanup is not completion. Partial synchronized micro/target counts, FB-only and audit-inclusive peak, source/CP/tokenizer/cleanup proofs are in new JSON."
exit "$result"
