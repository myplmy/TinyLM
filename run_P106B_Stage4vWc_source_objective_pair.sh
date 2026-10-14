#!/usr/bin/env bash
# CPU same-source/parent/update/objective target readback; quality is offline.
# Estimated0.02h; no input/model/download/cleanup/old overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4vWc_source_objective_pair_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4vWc_source_objective_pair_"$stamp" --num 101 --note 'Compare same source/body/SFT exposure and reference target events, native CE and actual answers separately. Parsed/literal agreement is not semantic quality. Corpus/model/source raw stay local.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4vWc_source_objective_pair_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_compare.py --execute
