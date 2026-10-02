#!/usr/bin/env bash
# P106B_Stage3qWa_lexical_ab_cpu: expected 0.05h. CPU-only frozen answer A within versus B bounded recent queue; latency is not live GPU speed or semantic quality.
# New stage/version only; originals preserved; every prerequisite failure stops this launcher.
# No interactive input. CPU/static success does not imply new teacher/student quality.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3qWa_lexical_ab_cpu.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3qWa_lexical_ab_cpu --num 101 --note 'CPU-only frozen answer A within versus B bounded recent queue; latency is not live GPU speed or semantic quality. Read raw answers and report domains separately. Admission is not truth; no stdin wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage3qWa_lexical_ab_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3qWa_lexical_ab_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3qWa_lexical_ab_cpu --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_lexical_modes.py --execute
