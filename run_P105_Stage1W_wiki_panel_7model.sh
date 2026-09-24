#!/usr/bin/env bash
# P105 Stage1W: user-run seven existing checkpoints, 20 prompts x 2 decodes each.
# GPU/model only by user, estimated 1-3 h, run alone after a current smoke PASS.
# The future chat32 SFT arm is absent and intentionally excluded, not silently canceled.
# Output is write-once JSONL; failure retains a .partial file and exits nonzero.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
out="runs/bench/p105_stage1w_wiki_panel_7model.jsonl"
cmd=( "$python_bin" -B -X utf8 scripts/eval_p105_wiki_panel.py
    --model 'd18_cla2_norecur_rms4,ko-en,dense,m100s14,300M'
    --model 'dense_chat32_p090b_s1337,ko-en,dense,m100s10,300M,chat32'
    --model 'p097_ctrl_v2,ko-en-control-v2,dense,m100s10,300M'
    --model 'p097_fw2,ko-en-fw2,dense,m100s10,300M'
    --model 'd14_cla2_norecur_rms4_lr15,ko-en,dense,m100s10,300M'
    --model 'd14_cla2_norecur_rms4_t600,ko-en,dense,m100s10,600M'
    --model 'd16_cla2_norecur_rms4_t1200,ko-en,dense,m100s12,1200M'
    --out "$out" --seed 20260925 --max-new 80 )
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1W_wiki_panel_7model --note "Seven documented model lineages, 4 strata x 5 prompts x 2 decodes = 280 outputs. Distinct pools/tokenizers are descriptive, not a quality ranking. Future chat32 SFT arm NOT_RUN."
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1W_wiki_panel_7model -- "${cmd[@]}" --check-only
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] metadata/lineage preflight rc=%s; no model run started\n' "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1W_wiki_panel_7model -- "${cmd[@]}"
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] generation rc=%s; preserve partial output and inspect before new suffix\n' "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1W_wiki_panel_7model -- "$python_bin" -B -X utf8 scripts/diag_p105_wiki_format.py --generation-jsonl "$out"
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] W0 frequency audit rc=%s\n' "$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 097 --name P105_Stage1W_wiki_panel_7model --note "Read raw answers by stratum; URL-request rows are not unwanted URLs. Actual EOS finish reason and semantic quality are NOT_MEASURED. Do not change the base dataset from this panel."
