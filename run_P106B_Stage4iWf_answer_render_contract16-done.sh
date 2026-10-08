#!/usr/bin/env bash
# User GPU estimate7-12min/max60min. Same pinned16 source/seed/Gemma MTPoff/card sampler, new output V2. Code renders only explicit scalar answer envelopes; preserves raw/trace. Need16 technical groups; not semantic PASS.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4iWf_answer_render_contract16"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWf_answer_render_contract16 --num 101 --note 'User GPU estimate7-12min/max60min. Same pinned16 source/seed/Gemma MTPoff/card sampler, new output V2. Code renders only explicit scalar answer envelopes; preserves raw/trace. Need16 technical groups; not semantic PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWf_answer_render_contract16 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_output_recovery.py --mode contract16 --execute
