#!/usr/bin/env bash
# P090B Stage0W: legacy/chat32/best-parent lineage and chat assistant-only mask.
# About 0.1 h CPU. No model training or protected held-out access.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0W_three_lineage_sft_gate --note "Arm A legacy tokenizer, arm B chat32 new parent, arm C selected-best parent remain separate lineages. No quality claim."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0W_three_lineage_sft_gate -- "$python_bin" -B -X utf8 scripts/diag_p090b_three_lineages.py
rc=$?
if [[ "$rc" -ne 0 ]]; then exit "$rc"; fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0W_three_lineage_sft_gate -- "$python_bin" -B -X utf8 scripts/diag_sft_mask.py --data ko-en
rc=$?
if [[ "$rc" -ne 0 ]]; then exit "$rc"; fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0W_three_lineage_sft_gate -- "$python_bin" -B -X utf8 scripts/train_sft_p090.py --self-test
