#!/usr/bin/env bash
# v12 matched work: native, original INT, native-forward hybrid, and same producer pack outputs.
# Reuses frozen original supervision; no model, training, checkpoint, or quality adoption.
# Explicit25Oct13KST; internal870s and independent external900s worker window.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p102a_accel_runtime/fused_ce_env_20261024/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe
source_pin=E4DAE0F849FCE8F87705FF8620D4835F2759DA2A91B06E87D3DA8EC98A8ACB88
zip_pin=E1397A0A2143B702EA187F492CF3B594636A62EA825F2DA383E9BC338FA8805E
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -I -B -X utf8 scripts/diag_p102a_v12_matched_pipeline.py --check-only
fi
"$python_bin" -I -B -X utf8 -c 'from datetime import datetime,timezone; end=datetime.fromisoformat("2026-10-25T04:00:00+00:00"); assert (end-datetime.now(timezone.utc)).total_seconds()>=930,"whole bound and external cleanup do not fit delegated deadline"' || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3dW_v12_matched_pipeline --note 'New matched pipeline only. Frozen originalD21 and first-GPU root19703B2D; companionE4DAE0F8. M32 full original CPU algebra precedes8192. Same BF16 operands, original INT and native-forward hybrid, terms0/2 codes/scales and original gradient exact; native approximation separate. Producer includes same y+7pack outputs in both arms. Cold/reused weight pack and compile/warmup2/measure5 separated. No model, checkpoints, full-training or quality adoption.'
timeout --signal=TERM --kill-after=5s 895s "$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3dW_v12_matched_pipeline -- "$python_bin" -I -B -X utf8 scripts/diag_p102a_v12_matched_pipeline.py --execute --expand --tag p102a_v12_matched_pipeline_v1_s1337_oct25a --source-sha256 "$source_pin" --original-zip-sha256 "$zip_pin" --deadline 2026-10-25T04:00:00+00:00 --max-wall-sec 870 --warmup 2 --measure 5
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 093 --name P102A_Stage3dW_v12_matched_pipeline --note "Actual root exit=$result. Require actual worker/supervisor exit, source/ZIP/prior closure invariance, original implementation checks, terminal without veto and owned cleanup. Standalone numerical/cost observation is not full-training speed, memory benefit or intelligence. Original first-GPU slower result remains unchanged."
exit "$result"
