#!/usr/bin/env bash
# P106B Stage2kW: exact public/protected source lineage census, READ-ONLY.
# Reads only named OASST2, public-v3 Aya and dictionary/word references.
# No teacher, model, GPU, protected text copy or dataset shard emission.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2kW_multisource_lineage_census.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2kW runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2kW_multisource_lineage_census --num 101 --note \
  'Read-only source census. Aya Dataset is CohereLabs/aya_dataset, not Aya Collection; old public-v3 oasst is OASST1, separate pinned OASST2 is counted. Dictionary JSON11/word27/TXT2 are exact protected references; no content copied or teacher input. Rights gate remains HOLD.'
"$python_bin" scripts/runlog.py --name P106B_Stage2kW_multisource_lineage_census --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_multisource_deck.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2kW_multisource_lineage_census --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_multisource_deck.py --check-only
