#!/usr/bin/env bash
# P090B Stage1bW: user-owned new chat32 parent, 300.024M draw/601M exact pool.
# One 16 GiB GPU, estimated 2-4 GPU-h after Stage1aW and WSL smoke PASS.
# No legacy parent, KD, resume or output overwrite; quality comparison is descriptive.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
for required in data_cache/tok-ko-en-32768-chat32.json data_cache/ko-en_601000000_chat32/meta.json data_cache/ko-en_601000000_chat32/train.bin data_cache/ko-en_601000000_chat32/val.bin; do
    if [[ ! -f "$required" ]]; then
        printf "[STOP] missing chat32 Stage1aW asset: %s\n" "$required" >&2
        exit 2
    fi
done
for output in runs/logs/m100s10_ko-en_300M_dense_chat32_p090b_s1337.json runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337_best.pt; do
    if [[ -e "$output" || -L "$output" ]]; then
        printf "[STOP] new-parent output exists: %s\n" "$output" >&2
        exit 2
    fi
done
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1bW_chat32_parent_300M -- "$python_bin" -B -X utf8 scripts/diag_p090b_chat32_sft_lengths.py \
    --manifest HF/sft_ready/p090_public_v3_manifest.json \
    --tokenizer data_cache/tok-ko-en-32768-chat32.json --max-seq 1024
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[STOP] chat32 public SFT context gate rc=%s; do not train parent\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1bW_chat32_parent_300M --note "New chat32 parent from scratch, same raw ko-en source family but different tokenizer/pool from legacy. Do not attribute A/B difference to tokenizer alone."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1bW_chat32_parent_300M -- "$python_bin" run100m.py train \
    --preset m100s10 --arch dense --data ko-en --tokens 300M --steps 2289 \
    --pool-tokens 601M --exact-cache --chat32-tokenizer \
    --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd \
    --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --no-ckpt \
    --ce-chunk 2048 --cla-group 2 --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --eval-every 100 --save-every 1000 \
    --tag dense_chat32_p090b_s1337
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[FAIL] chat32 parent training rc=%s; retain original log, no SFT continuation\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1bW_chat32_parent_300M --note "Read tokenizer_lineage and tokenizer_sha256 in checkpoint/JSON, n_skip and Korean/English fixed validation. Full SFT and tokenizer-effect attribution remain NOT_RUN."
