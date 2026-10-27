#!/usr/bin/env bash
# Independent NTP accounting/cost only; no optimizer or checkpoint writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode cost --max-wall-sec 900 --profile handoff/audit/oct27_independent/p013_context_profile_v2.json --profile-sha256 52D66CB45CF9A7A1FE3ADC3D989C7C5091710F6DFB8B5229420B608D43572825)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p013_context_curriculum.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P013_Stage1W_context_forward_backward_cost --num 106 --note "Exact same full1024 windows; NTP-only/R1/noKD/noMTP. Micro8 activeaccum64/32/16 keeps131072input/targets; preserved lasttarget and source RNG. Phase cost max 900s before27Oct17KST. No data cleanup/new300M/new training/optimizer/CP/quality claim. Cost is eagerBF16 ckptON F+B only; excludes optimizer/compile/eval/save."
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P013_Stage1W_context_forward_backward_cost --num 106 -- "$python_bin" -B -X utf8 scripts/diag_p013_context_curriculum.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P013_Stage1W_context_forward_backward_cost --num 106 --note "Final actual_exit=$result; fulltechnical0/budgetHOLD8/error9 separate. No whole-training or intelligence adoption; see actual source/profile/cleanup JSON."
exit "$result"
