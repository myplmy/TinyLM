#!/usr/bin/env bash
# Freeze independent public512/val64 original source deck; no models [Completed logical stage; archive in WIP_20261014b_LAUNCHER_ARCHIVE.json.]
# Estimated 0.05h; no stdin/download/cleanup/old overwrite; independent raw timestamp.
# Standard student: micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4u1W_public_source_deck_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u1W_public_source_deck_"$stamp" --num 101 --note 'Freeze independent public512/val64 original source deck; no models. Read measured versus not-run stages, scope and final verdict. Parsed fields/literal agreement are not semantic truth. Keep source raw/model/corpus local. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u1W_public_source_deck_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_course.py --mode freeze --execute
