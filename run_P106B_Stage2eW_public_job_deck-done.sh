#!/usr/bin/env bash
# P106B Stage2eW: CPU-only finite local public-v3 teacher job deck.
# Source v3 is read-only; new ignored HF job shards are <=20MB, write-once.
# No teacher/student model, download, checkpoint or training.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage2eW_public_job_deck.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage2eW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2eW_public_job_deck --num 101 --note \
  'Finite local public-v3 source IDs. One variant per concept/language, split before teacher generation, no repetitive seed loop. Heuristic topics are coverage diagnostics, not quality evidence.'
"$python_bin" scripts/runlog.py --name P106B_Stage2eW_public_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_job_deck.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2eW_public_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_job_deck.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2eW_public_job_deck --num 101 --note \
  'Write-once HF job shards <=20MB and exact source manifest. This deck is not a 50:50 token-balanced or 300M training corpus; missing topics remain explicit.'
"$python_bin" scripts/runlog.py --name P106B_Stage2eW_public_job_deck --num 101 -- \
  "$python_bin" -B -X utf8 scripts/build_p106b_job_deck.py --execute
