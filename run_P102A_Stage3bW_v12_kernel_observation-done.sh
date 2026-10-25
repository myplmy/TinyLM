#!/usr/bin/env bash
# Standalone v12 CUDA kernels; no model, training, or checkpoint output.
# Expand only after the small implementation checks; no quality adoption.
# Whole OS window at most900s; actual timing and memory are not full-training claims.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p102a_accel_runtime/fused_ce_env_20261024/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
source_pin=D21DC21C647516A13B7FADCA87DAA4893943A59EC7DCAC8F46B9374BF5EA004B
zip_pin=E1397A0A2143B702EA187F492CF3B594636A62EA825F2DA383E9BC338FA8805E
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p102a_v12_kernels.py --check-only
fi
"$python_bin" -B -X utf8 -c 'from datetime import datetime,timezone; d=datetime.fromisoformat("2026-10-25T04:00:00+00:00"); assert (d-datetime.now(timezone.utc)).total_seconds()>=930,"whole cap and external cleanup do not fit delegated deadline"' || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3bW_v12_kernel_observation --note 'Actual v12 CUDA implementation and cost observation. M32 full oracles precede M8192 sampled CPU oracle and full transpose controls. Original strict pack/integer VJP contract, separate native approximation, producer BF16 ULP and pack checks. Fresh namespace, internal870s and external900s whole window. No model update, quality, or speed adoption.'
timeout --signal=TERM --kill-after=5s 895s "$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3bW_v12_kernel_observation -- "$python_bin" -B -X utf8 scripts/diag_p102a_v12_kernels.py --execute --expand --tag p102a_v12_kernel_v1_s1337_oct25a --source-sha256 "$source_pin" --original-zip-sha256 "$zip_pin" --deadline 2026-10-25T04:00:00+00:00 --max-wall-sec 870 --warmup 2 --measure 5
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3bW_v12_kernel_observation --note "Actual root exit=$result. Accept only complete implementation observations with actual worker/supervisor exit, matching sources, no terminal veto, and owned cleanup. Native approximation and whole-training usefulness remain separate."
exit "$result"
