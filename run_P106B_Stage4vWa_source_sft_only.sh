#!/usr/bin/env bash
# Same originalparent micro8 accum16 ckptON LR5e-5 Muon2e-4 four passes; SFT-only
# Estimated 0.25h; no stdin/download/cleanup/old overwrite; independent raw timestamp.
# Standard student: micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4vWa_source_sft_only_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4vWa_source_sft_only_"$stamp" --num 101 --note 'Same originalparent micro8 accum16 ckptON LR5e-5 Muon2e-4 four passes; SFT-only. Read measured versus not-run stages, scope and final verdict. Parsed fields/literal agreement are not semantic truth. Keep source raw/model/corpus local. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4vWa_source_sft_only_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_course.py --mode train --arm sft_only --max-wall-sec 1200 --execute
