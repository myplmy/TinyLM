#!/usr/bin/env bash
# Conditional on completed replay3/test. CPU contracts, then new code-proven pairs/test.
# Approx0.03h CPU. Source replay100 is a development choice; no model run here.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ag0W_conditional_pair_contract_"$stamp" --note 'CPU contracts and fresh pair corpus. Only original code one-value contracts; public/unknown/normal repetition are not judged. Original replay3 and sealed test must be complete. New640 test, old test is now development.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ag0W_conditional_pair_contract_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_conditional_orpo.py
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ag0W_conditional_pair_contract_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode freeze --replay-source replay100 --decision-note 'Development-selected native replay; previous three-arm report and result101 own the exact tradeoff, not a world-quality claim' --execute
