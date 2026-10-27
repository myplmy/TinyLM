#!/usr/bin/env bash
# Explicit new CPU5400s cap; original1800s HOLD and completedCUDA lane stay intact.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--max-wall-sec 5400 --profile handoff/audit/oct27_independent/gguf_cpu_continuation_profile_v1.json --profile-sha256 43D6713F82723538645932625B490F2E0D7CC938EAD4B0840D382DF670DBC6F4)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_cpu_resume.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11hW_gpt2_cpu_budget_continuation --num 101 --note 'Untouched originalCPU HOLD8 actual27611; measured conservative3802.180s+600s fits a new5400s cap and27Oct17KST. Prior metadata1800 contract validation is distinct from real5400 wall/Budget/native deadline. Same35 source/build/asset/singleton full4contexts fixed32 warm1/timed3/observed3/natural64. No CUDA lane rerun, no sample/tolerance shrink or original report edit. CPU offload0 still discovers native backends/NVML. No training/new300M/install/download; exact nativeKV/storage unmeasured.'
timeout --signal=TERM --kill-after=20s 5460s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11hW_gpt2_cpu_budget_continuation --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_cpu_resume.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11hW_gpt2_cpu_budget_continuation --num 101 --note "Final newCPU5400 phase exit=$result. Preserve original1800 HOLD8; full0, newHOLD8 and error9 separate. Compare actual answers and actual singleton policy, no quality/default-speed adoption."
exit "$result"
