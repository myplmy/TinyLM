#!/usr/bin/env bash
# Cost8 prerequisite; same parent/SFT/native inputs, native weight0. About 0.25h GPU.
# SFT micro8 accum16 seq1024 ckptON four passes176 updates; no MTP or W&B probe upload.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWa_sft_no_replay_"${stamp}" --note 'SFT baseline weight0. Same native forward/CE, zero native gradient. Four passes176 updates, real SFT and auxiliary inputs separate. Final sealed code test follows all three arms; public teacher agreement is not truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWa_sft_no_replay_"${stamp}" -- "$python_bin" -B -X utf8 scripts/diag_p106b_retention_course.py --mode train --arm sft_only --execute --max-wall-sec 3600
