#!/usr/bin/env bash
# P090B Stage1cW: same raw bilingual prompts on three legacy ko-en parents.
# About 0.3 GPU-h, inference only. Parent choice is not an automatic score.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1cW_best_parent_panel --note "Three legacy ko-en parents: d14 300M, d14 600M, d16 1200M. Same raw KO/EN prompts, different pretraining budgets/structures; no automatic best-parent claim."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1cW_best_parent_panel -- "$python_bin" -B -X utf8 scripts/eval_p100_capability_panel.py \
    --model d14_cla2_norecur_rms4_lr15,ko-en,dense,m100s10,300M \
    --model d14_cla2_norecur_rms4_t600,ko-en,dense,m100s10,600M \
    --model d16_cla2_norecur_rms4_t1200,ko-en,dense,m100s12,1200M \
    --out runs/bench/p090b_stage1c_best_parent_panel.jsonl --max-new 80 --check-only
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[STOP] P090B parent inventory failed rc=%s\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1cW_best_parent_panel -- "$python_bin" -B -X utf8 scripts/eval_p100_capability_panel.py \
    --model d14_cla2_norecur_rms4_lr15,ko-en,dense,m100s10,300M \
    --model d14_cla2_norecur_rms4_t600,ko-en,dense,m100s10,600M \
    --model d16_cla2_norecur_rms4_t1200,ko-en,dense,m100s12,1200M \
    --out runs/bench/p090b_stage1c_best_parent_panel.jsonl --max-new 80
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf "[FAIL] P090B common raw-answer panel rc=%s\n" "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage1cW_best_parent_panel --note "Review saved full answers by KO/EN knowledge, context, format, short memory and logic; P097 common benchmark and parent tokenizer lineage remain separate. Select C only after evidence review."
