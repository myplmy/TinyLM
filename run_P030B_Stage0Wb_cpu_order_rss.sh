#!/usr/bin/env bash
# P030B Stage0Wb: repeat same d14 final checkpoints in A-B-B-A order to separate order drift.
# User-run CPU-only, about 1.0 h upper budget. Each command is a fresh process.
# Same int8-store/unpack-cache/last-only/1-thread/128-token conditions as Stage0W.
# A failed arm does not erase the other rows; the panel exits nonzero if any arm fails.
set -uo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
"$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 --note \
  'A/B/B/A fresh-process CPU1 throughput and matching fresh-process RSS; physical int8-store+unpack-cache remains over 40MiB until separately disproved. Same checkpoint families and prompt as Stage0W; order is the only panel change.'
"$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 -- \
  "$python_bin" -B -X utf8 scripts/paired_eval.py --preset m100s10 --data ko-en \
  --tokens 300M --ckpt-tokens 300M --models d14_cla2_norecur d14_cla2_norecur_rms4 \
  --check-inputs || exit 9

errors=0
for tag in d14_cla2_norecur d14_cla2_norecur_rms4 d14_cla2_norecur_rms4 d14_cla2_norecur; do
  "$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 --note \
    "CPU benchmark fresh process tag=$tag; A/B/B/A order, reps3, 1 thread, last-only, 128 decode tokens."
  "$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 -- \
    "$python_bin" -B -X utf8 scripts/bench_infer.py --models "$tag" \
    --preset m100s10 --data ko-en --tokens 300M --device cpu --threads 1 \
    --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache \
    --logits-last-only --check-cache --cpu-watch --cpu-baseline 10 --require-all || errors=$((errors + 1))
done
for tag in d14_cla2_norecur d14_cla2_norecur_rms4 d14_cla2_norecur_rms4 d14_cla2_norecur; do
  "$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 --note \
    "CPU residency fresh process tag=$tag; tensor/runtime accounting and RSS are not packed-file bytes."
  "$python_bin" scripts/runlog.py --name P030B_Stage0Wb_cpu_order_rss --num 100 -- \
    "$python_bin" -B -X utf8 scripts/mem_runtime.py --models "$tag" \
    --preset m100s10 --data ko-en --tokens 300M --device cpu \
    --drop-latent --int8-store --unpack-cache --kv-seq 1024 --kv-dtype fp32 --require-all || errors=$((errors + 1))
done
if [[ "$errors" -ne 0 ]]; then
  printf '[FAIL] P030B Stage0Wb had %s execution errors; all available rows were preserved\n' "$errors" >&2
  exit 9
fi
printf '%s\n' '[COLLECTED] P030B Stage0Wb ABBA throughput/RSS rows; optimizer inference causality and 40MiB adoption remain separate.'
