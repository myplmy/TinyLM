#!/usr/bin/env bash
# CPU readback of already frozen source deck; no duplicate generation or model. [Completed logical stage; archive in WIP_20261014b_LAUNCHER_ARCHIVE.json.]
# Estimated0.02h; original freeze ran through direct API, this verifies it.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4u1Wb_saved_source_deck_readback_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u1Wb_saved_source_deck_readback_"$stamp" --num 101 --note 'Existing frozen source deck identity/lane/document disjointness only. No source regeneration, model, truth verifier, download or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u1Wb_saved_source_deck_readback_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_deck_readback.py
