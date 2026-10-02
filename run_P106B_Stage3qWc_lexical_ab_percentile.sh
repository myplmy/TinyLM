#!/usr/bin/env bash
# P106B_Stage3qWc_lexical_ab_percentile: expected 0.05h. CPU-only frozen lexical A/B, corrected nearest-rank percentile; no truth or live GPU adoption.
# New stage, immutable originals. No interactive input; every prerequisite stops this launcher.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3qWc_lexical_ab_percentile.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3qWc_lexical_ab_percentile --num 101 --note 'CPU-only frozen lexical A/B, corrected nearest-rank percentile; no truth or live GPU adoption.'
"$python_bin" scripts/runlog.py --name P106B_Stage3qWc_lexical_ab_percentile --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_output_contract.py
"$python_bin" scripts/runlog.py --name P106B_Stage3qWc_lexical_ab_percentile --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3qWc_lexical_ab_percentile --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3qWc_lexical_ab_percentile --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --execute
