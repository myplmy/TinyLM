#!/usr/bin/env bash
# P097 Stage2W: evaluate four completed recipe checkpoints on identical task IDs,
# common bytes and deterministic continuation prompts. Training/download: 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
items="runs/bench/p097_stage2_panel.jsonl"
prompts="runs/bench/p097_stage2_prompts.jsonl"

"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation \
  --note "P097 Stage2W: same task IDs with per-checkpoint tokenizer/data, common byte bpb, and deterministic prompt panel; training 0" \
  || exit $?
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/check_p097_stage2_assets.py \
  --outputs "$items" "$prompts" || exit $?

failures=0
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task kobest_copa --n 1000 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 kobest_copa failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task kobest_hellaswag --n 500 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 kobest_hellaswag failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task klue_ynat --n 1000 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 klue_ynat failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task klue_nli --n 1000 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 klue_nli failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task arc_easy_full --n 1200 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 arc_easy_full failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_bench_suite.py --task hellaswag --n 1200 \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad --model-arch dense \
  --preset m100s10 --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$items" \
  || { printf '%s\n' '[WARN] P097 Stage2 hellaswag failed' >&2; failures=$((failures + 1)); }

"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/common_bpb.py --preset m100s10 --tokens 300M \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad \
  --arch dense dense dense dense \
  --max-docs 1000 --micro-bs 4 --ce-chunk 1024 --device cuda \
  || { printf '%s\n' '[WARN] P097 Stage2 common-bpb failed' >&2; failures=$((failures + 1)); }

"$python_bin" scripts/runlog.py --num 090 --name P097_Stage2W_common_recipe_evaluation -- \
  "$python_bin" scripts/eval_recipe_prompt_panel.py \
  --models p097_ctrl_v2 p097_fw2 p097_edu_v2 p097_madlad \
  --model-data ko-en-control-v2 ko-en-fw2 ko-en-edu-v2 ko-en-madlad \
  --model-arch dense --preset m100s10 --tokens 300M \
  --max-new 80 --device cuda --out "$prompts" \
  || { printf '%s\n' '[WARN] P097 Stage2 prompt panel failed' >&2; failures=$((failures + 1)); }

if (( failures > 0 )); then
  printf '[FAIL] P097 Stage2 component failures=%d; inspect result 090 log\n' "$failures" >&2
  exit 4
fi
printf '%s\n' '[PASS] P097 Stage2 panel complete; cross-recipe ranking requires result analysis.'
