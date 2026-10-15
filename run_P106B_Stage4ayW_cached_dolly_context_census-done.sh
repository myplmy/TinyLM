#!/usr/bin/env bash
# Executed2026-10-15 raw114520 exit9: v1 census used strict student encoder before long-row count. Source/report preserved.
# CPU only: two cached Dolly files, source SHA, full serialization counts and exact-span candidates.
# Not a semantic validator or training admission. Raw candidates remain separate ignored local/HF.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ayW_cached_dolly_context_census_"$stamp" --note 'CPU raw counts/technical exact alignment only. Models/GPU/download0. Original public sources read-only. Dolly-derived candidates isolated and not admitted to main training.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ayW_cached_dolly_context_census_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_dolly_context_census.py --execute --max-wall-sec 1200
