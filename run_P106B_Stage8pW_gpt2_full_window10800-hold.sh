#!/usr/bin/env bash
# HOLD unused v1: independent review found report-closure timing boundary gap.
# GPT2 full only: frozen native v2 numerical/cost receipts reused unchanged.
# Separate10800s owner, not a relaxed numerical gate or a replay of old7200HOLD.
# Whole cap must fit24Oct08:40KST. No input wait, installation, training or CP save.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_window.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pW_gpt2_full_window10800_"$stamp" --note 'GPT2 full only, owner sourceBA9C6E52, frozen evaluator42713A9E and original strict canary/cost/HOLD SHAs. Official19965rows67106choices, singleton quantized native path unchanged. Measured forecast8734.442sec, cap10800sec, full window must fit24Oct08:40KST. Previous7200HOLD remains NOT_RUN, not score0. One GPU, no training/install.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pW_gpt2_full_window10800_"$stamp" -- "$python_bin" -B -X utf8 scripts/p106b_native_window.py --execute --model gpt2_q4km --mode full --source-sha256 BA9C6E52D5D402B35AF47C58F137D9DFEE2056127DA0EC55A214CC656F58F081 --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec 10800
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pW_gpt2_full_window10800_"$stamp" --note "Window exit=$result. Domain HOLD=8, actual error or closure failure=9. Only a closed full19965/67106 plus raw recount/source/model/cleanup checks permits a score. Inner sample tag is frozen v2 origin, owner tag is separate. Resource samples/gaps do not prove continuous peak/OOM safety."
exit "$result"
