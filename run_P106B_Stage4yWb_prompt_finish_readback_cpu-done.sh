#!/usr/bin/env bash
# Preserve prior256 answers. CPU-only finish_reason counter recovery and four regressions. [Completed logical stage; archive in WIP_20261014b_LAUNCHER_ARCHIVE.json.]
# No new model/generation/train. Approx0.02h. Original verdict and code preserved in cf3ee25.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4yWb_prompt_finish_readback_cpu_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4yWb_prompt_finish_readback_cpu_"$stamp" --num 101 --note 'CPU regression then recompute finish_reason counts from immutable256 answers. No model/generation/checkpoint write. Literal agreement/empty counts must not change; old wrong summary retained.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4yWb_prompt_finish_readback_cpu_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_source_prompt_pair.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4yWb_prompt_finish_readback_cpu_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_prompt_pair.py --readback
