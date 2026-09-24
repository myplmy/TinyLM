#!/usr/bin/env bash
# P103A Stage0bW: exact-token prefix structure in public SFT v3 only.
# CPU/read-only about 0.1 h. Protected TinyDataset and model/GPU are excluded.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0bW_public_sft_prefix_census --note "Manifest SHA, exact ChatML token IDs and min-prefix 32/64/128. This measures only corpus structural opportunities, not training wall speed."
for min_prefix in 32 64 128; do
    "$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0bW_public_sft_prefix_census -- "$python_bin" -B -X utf8 scripts/diag_p103a_prefix_census.py \
        --input HF/sft_ready/p090_public_v3_train.canonical.jsonl \
        --manifest HF/sft_ready/p090_public_v3_manifest.json \
        --tokenizer data_cache/tok-ko-en-32768.json \
        --min-prefix "$min_prefix" --max-branches 4
    rc=$?
    if [[ "$rc" -ne 0 ]]; then
        printf "[FAIL] P103A public prefix census min=%s rc=%s\n" "$min_prefix" "$rc" >&2
        exit "$rc"
    fi
done
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0bW_public_sft_prefix_census --note "Public v3 is not TRAIN_READY while contamination/source-quality gates are NOT_RUN. KnowledgePack duplicate rate and Transformer wall remain unknown."
