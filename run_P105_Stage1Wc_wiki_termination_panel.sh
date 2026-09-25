#!/usr/bin/env bash
# P105: rerun the same seven-model panel with measured EOS/max-new reason.
# Cost: about 1-3 h user model/GPU or CPU, separate from the old 280-row output.
# Dependent stages abort on preflight, generation, or audit error.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
name=P105_Stage1Wc_wiki_termination_panel
output=runs/bench/p105_stage1wc_wiki_termination_7model.jsonl
run_panel() {
  "$python_bin" scripts/runlog.py --num 097 --name "$name" -- "$python_bin" -B -X utf8 scripts/eval_p105_wiki_panel.py \
    --model d18_cla2_norecur_rms4,ko-en,dense,m100s14,300M \
    --model dense_chat32_p090b_s1337,ko-en,dense,m100s10,300M,chat32 \
    --model p097_ctrl_v2,ko-en-control-v2,dense,m100s10,300M \
    --model p097_fw2,ko-en-fw2,dense,m100s10,300M \
    --model d14_cla2_norecur_rms4_lr15,ko-en,dense,m100s10,300M \
    --model d14_cla2_norecur_rms4_t600,ko-en,dense,m100s10,600M \
    --model d16_cla2_norecur_rms4_t1200,ko-en,dense,m100s12,1200M \
    --out "$output" --seed 20260925 --max-new 80 --record-termination "$@"
}
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1Wc_wiki_termination_panel --note "P105 Stage1Wc: same seven lineages and prompts as Stage1W, separate write-once output. No causal source/SFT claim."
"$python_bin" scripts/runlog.py --num 097 --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p105_termination_audit.py --self-test
run_panel --check-only
run_panel
"$python_bin" scripts/runlog.py --num 097 --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p105_termination_audit.py --input-jsonl "$output"
"$python_bin" scripts/runlog.py --num 097 --name "$name" --note "Compare EOS and max-new by model/stratum with repetition; do not infer source or quality causality."
