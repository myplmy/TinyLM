#!/usr/bin/env bash
# Exact IQ2 full evaluation; original scoring and strict canary preserved.
# Fresh worker changes only the authorized date bound and its message.
# Forecast15314s; parent cap17400s including cleanup before25Oct13KST.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
source_pin=4CF29AB6BB5BEB0090741C6096B05B15E2C08D5AA3A6869E617FD08DDBE6F3BA
prior_log=test_result/101_log_20261024_P106B_Stage8jWd_qwen_iq2_singleton_core6_20261023T172207Z.txt
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_iq2_window.py --check-only
fi
"$python_bin" -B -X utf8 -c 'from datetime import datetime,timezone; d=datetime.fromisoformat("2026-10-25T04:00:00+00:00"); assert (d-datetime.now(timezone.utc)).total_seconds()>=17430,"whole cap and external cleanup do not fit delegated deadline"' || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWh_iq2_supervised_full --note 'Exact Qwen3.5-0.8B IQ2 singleton full;19965 documents/67106 choices planned. Fresh date-only worker; unchanged numerical tolerances and official tasks. Controller cap17400s includes60s supervisor cleanup. No quality adoption before complete official evidence.'
timeout --signal=TERM --kill-after=15s 17415s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWh_iq2_supervised_full -- "$python_bin" -B -X utf8 scripts/p106b_native_iq2_window.py --supervise --model qwen35_08b_iq2xxs --mode full --source-sha256 "$source_pin" --deadline 2026-10-25T04:00:00+00:00 --max-wall-sec 17400 --prior-run-log "$prior_log"
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWh_iq2_supervised_full --note "Actual root exit=$result. Require actual supervisor and controller exit0, complete choice wires, strict numerical pass, no terminal veto and owned-worker cleanup before accepting scores."
exit "$result"
