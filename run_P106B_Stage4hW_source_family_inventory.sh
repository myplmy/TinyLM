#!/usr/bin/env bash
# User CPU0.5h estimate; exact12 public sources, metadata/current routing counts.
# Hash samples8 per family/language, sample token checks, no whole-token claim.
# No stdin/GPU/teacher/downloads/old corpus writes. New inventory path only.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4hW_source_family_inventory.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4hW_source_family_inventory --num 101 --note 'User CPU0.5h estimate; exact12 public sources/current routing counts and hash sample8/family-language. Unassigned is not bad quality; sample tokens are not measured whole supply. New inventory only, no teacher/GPU/downloads; new smoke first.'
"$python_bin" scripts/runlog.py --name P106B_Stage4hW_source_family_inventory --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_inventory.py --execute
