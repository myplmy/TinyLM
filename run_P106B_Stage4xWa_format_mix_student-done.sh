#!/usr/bin/env bash
# Same parent micro8 accum16 seq1024 ckptON LR5e-5 Muon2e-4 four passes32; prompt lengths intentionally differ [Completed logical stage; archive in WIP_20261014b_LAUNCHER_ARCHIVE.json.]
# Estimated .25h; no stdin/download/cleanup; independent raw timestamp.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4xWa_format_mix_student_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4xWa_format_mix_student_"$stamp" --num 101 --note 'Same parent micro8 accum16 seq1024 ckptON LR5e-5 Muon2e-4 four passes32; prompt lengths intentionally differ. Read execution, actual token counts, raw answers and final verdict separately. Literal agreement is not semantic truth. Keep third party source raw local.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4xWa_format_mix_student_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_format_mix.py --mode train --execute --max-wall-sec 1200
