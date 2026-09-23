#!/usr/bin/env bash
# P090B Stage1aW: user-owned new chat32 tokenizer and isolated 601M exact cache.
# CPU/network/storage preparation, estimated 1-3 h. No model or GPU quality claim.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1aW_chat32_prepare --note "New chat32 token IDs; preserve legacy tokenizer/cache. 601M pool exceeds 2x 300,023,808 draw tokens. User owns network/cache creation."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1aW_chat32_prepare -- "$python_bin" run100m.py prepare --data ko-en --tokens 601M --exact-cache --chat32-tokenizer
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[FAIL] chat32 tokenizer/cache prepare rc=%s; do not train\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1aW_chat32_prepare -- "$python_bin" -B -X utf8 scripts/diag_p090b_three_lineages.py --chat32-tokenizer data_cache/tok-ko-en-32768-chat32.json
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[FAIL] chat32 special-token inventory rc=%s; do not train\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1aW_chat32_prepare -- "$python_bin" -B -X utf8 scripts/diag_p090b_chat32_sft_lengths.py \
    --manifest HF/sft_ready/p090_public_v3_manifest.json \
    --tokenizer data_cache/tok-ko-en-32768-chat32.json --max-seq 1024
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[GATE] chat32 public SFT re-encoding rc=%s; fix corpus before Stage1bW\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1aW_chat32_prepare --note "Inspect metadata/hash, source mix, Korean validation and disk use before Stage1bW. Tokenizer creation is not a new-parent quality PASS."
