#!/usr/bin/env bash
# P090B Stage0bW: public v3 SFT aggregate gate, no raw text printed.
# Read-only CPU under HF/sft_ready; contamination/manual quality remain separate.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0bW_public_sft_preflight --note "Aggregate split/mask/hash contract only; exit0 can still mean PILOT_ONLY when contamination or source quality is NOT_RUN."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0bW_public_sft_preflight -- "$python_bin" -B -X utf8 scripts/diag_p090b_public_preflight.py \
    --manifest HF/sft_ready/p090_public_v3_manifest.json \
    --tokenizer data_cache/tok-ko-en-32768.json
