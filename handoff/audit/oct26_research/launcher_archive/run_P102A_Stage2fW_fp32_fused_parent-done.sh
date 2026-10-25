#!/usr/bin/env bash
# Official CE FP32 three-arm numerical diagnosis; original six arms remain unchanged.
# Same parent, first128 rows, m8a16 fixed1024 checkpoint-on and original optimizer.
# At most900s whole OS window; instrumented first updates are not training speed.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p102a_accel_runtime/fused_ce_env_20261024/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
source_pin=20E2D751D1A880E113E144ABA008BBFA08931C9FC310C6DE3D8FB642F14DD1DF
dependency_pin=5DC506E34FEB1718EFBB8C2A6788E67DCBFC8002F4BF021A2D6B763726D4325F
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p102a_fused_ce_fp32.py --check-only
fi
"$python_bin" -B -X utf8 -c 'from datetime import datetime,timezone; d=datetime.fromisoformat("2026-10-25T04:00:00+00:00"); assert (d-datetime.now(timezone.utc)).total_seconds()>=930,"whole cap and external cleanup do not fit delegated deadline"' || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2fW_fp32_fused_parent --note 'FP32-only fresh reference/Liger/CCE each1update, first128 fixed V3 rows as numerical control only. Same m8a16 seq1024 checkpoint-on seed1337 Adam/Muon and strict loss/gradient/update tolerances. Original BF16 negative and six-arm contract unchanged. CPU captures are bounded8GiB. Internal870s and external900s window, checkpoint0, no quality or speed adoption.'
timeout --signal=TERM --kill-after=5s 895s "$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2fW_fp32_fused_parent -- "$python_bin" -B -X utf8 scripts/diag_p102a_fused_ce_fp32.py --execute --tag p102a_fused_ce_fp32_v1_s1337_oct25a --source-sha256 "$source_pin" --dependency-sha256 "$dependency_pin" --deadline 2026-10-25T04:00:00+00:00 --max-wall-sec 870
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage2fW_fp32_fused_parent --note "Actual root exit=$result. Complete numerical negative8 differs from error9. Require source/assets invariance, all157 and85 matrix comparisons, same-gradient and actual-update replays, actual worker/supervisor exit and owned cleanup. No full-training or BF16 adoption."
exit "$result"
