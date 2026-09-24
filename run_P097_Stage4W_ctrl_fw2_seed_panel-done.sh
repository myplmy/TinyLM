#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
items="runs/bench/p097_stage4_seed_panel.jsonl"
failures=0
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage4W_ctrl_fw2_seed_panel -- \
  "$python_bin" scripts/eval_bench_suite.py --task klue_ynat --n 1200 \
    --models p097_ctrl_v2 p097_fw2 p097_ctrl_v2_s2024 p097_fw2_s2024 p097_ctrl_v2_s31415 p097_fw2_s31415 \
    --model-data ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 \
    --model-arch dense dense dense dense dense dense --preset m100s10 --tokens 300M \
    --seq-max 1024 --seed 99 --device cuda --per-item-jsonl "$items" --wandb \
  || { printf '%s\n' '[WARN] P097 Stage4 klue_ynat failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage4W_ctrl_fw2_seed_panel -- \
  "$python_bin" scripts/eval_bench_suite.py --task klue_nli --n 1200 \
    --models p097_ctrl_v2 p097_fw2 p097_ctrl_v2_s2024 p097_fw2_s2024 p097_ctrl_v2_s31415 p097_fw2_s31415 \
    --model-data ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 \
    --model-arch dense dense dense dense dense dense --preset m100s10 --tokens 300M \
    --seq-max 1024 --seed 99 --device cuda --per-item-jsonl "$items" --wandb \
  || { printf '%s\n' '[WARN] P097 Stage4 klue_nli failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage4W_ctrl_fw2_seed_panel -- \
  "$python_bin" scripts/eval_bench_suite.py --task arc_easy_full --n 1200 \
    --models p097_ctrl_v2 p097_fw2 p097_ctrl_v2_s2024 p097_fw2_s2024 p097_ctrl_v2_s31415 p097_fw2_s31415 \
    --model-data ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 \
    --model-arch dense dense dense dense dense dense --preset m100s10 --tokens 300M \
    --seq-max 1024 --seed 99 --device cuda --per-item-jsonl "$items" --wandb \
  || { printf '%s\n' '[WARN] P097 Stage4 arc_easy_full failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage4W_ctrl_fw2_seed_panel -- \
  "$python_bin" scripts/eval_bench_suite.py --task hellaswag --n 1200 \
    --models p097_ctrl_v2 p097_fw2 p097_ctrl_v2_s2024 p097_fw2_s2024 p097_ctrl_v2_s31415 p097_fw2_s31415 \
    --model-data ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 \
    --model-arch dense dense dense dense dense dense --preset m100s10 --tokens 300M \
    --seq-max 1024 --seed 99 --device cuda --per-item-jsonl "$items" --wandb \
  || { printf '%s\n' '[WARN] P097 Stage4 hellaswag failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage4W_ctrl_fw2_seed_panel -- \
  "$python_bin" scripts/common_bpb.py --preset m100s10 --tokens 300M \
    --models p097_ctrl_v2 p097_fw2 p097_ctrl_v2_s2024 p097_fw2_s2024 p097_ctrl_v2_s31415 p097_fw2_s31415 \
    --data ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 ko-en-control-v2 ko-en-fw2 \
    --arch dense dense dense dense dense dense --max-docs 1000 --micro-bs 4 \
    --ce-chunk 1024 --device cuda \
  || { printf '%s\n' '[WARN] P097 Stage4 common-bpb failed' >&2; failures=$((failures + 1)); }
exit "$failures"
