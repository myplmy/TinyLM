#!/usr/bin/env bash
# P106B_Stage4faWf_broad_recovery_mixed_answers: metadata recovery only, pinned v1 scientific payload unchanged.
# Same22528 rows, two passes352, mixed versus staged; fail dependent stage only.
# No stdin, download, original mutation, or automatic quality verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4faWf_broad_recovery_mixed_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4faWf_broad_recovery_mixed_answers_"$run_stamp" --num 101 --note 'Regression90, metadata-key separation and independent byte/course/selection equivalence are required. v1 failure remains preserved. Same m8a16ckptON/native windows and two-pass352 design. Prior1694 and new actual-history16dialogues are separate. Costs require launcher start after five-minute idle. Estimated .5h GPU=D, worker cap1800s. Resource or stage success is not general intelligence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4faWf_broad_recovery_mixed_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_broad_recovery.py --mode evaluate --arm mixed --max-wall-sec 1800 --execute
