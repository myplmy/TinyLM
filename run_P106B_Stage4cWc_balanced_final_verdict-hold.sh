#!/usr/bin/env bash
# P106B_Stage4cWc_balanced_final_verdict: HOLD until75M bilingual corpus and matching wire are ready; original micro8/accum16/checkpoint-on/four passes,12h estimate. No teacher or student starts before data prerequisite.
# User execution only. Every phase and one final verdict share the runlog.
# Missing prerequisites stop dependent execution; no stdin/pause.
set -euo pipefail
case "${0##*/}" in
  *-hold.sh|*-HOLD.sh)
    printf '%s\n' '[HOLD] Explicitly held launcher. Review prerequisites and remove the suffix only after a new user decision.' >&2
    exit 8
    ;;
esac
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cWc_balanced_final_verdict.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4cWc_balanced_final_verdict --num 101 --note 'HOLD until75M bilingual corpus and matching wire are ready; original micro8/accum16/checkpoint-on/four passes,12h estimate. No teacher or student starts before data prerequisite. Read EXPERIMENT_FINAL, not just an intermediate child exit0/file size.'
"$python_bin" scripts/runlog.py --name P106B_Stage4cWc_balanced_final_verdict --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_stage_receipt.py --name P106B_Stage4cWc_balanced_final_verdict --mode balanced --execute
