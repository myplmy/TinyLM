#!/usr/bin/env bash
# Same payload and baseline; only output row tiles128/512/4096 change.
# Report all96 comparisons, retaining original tolerance failures; no adoption.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode diagnose --max-wall-sec 900 --profile handoff/audit/oct27_independent/packed_shape_profile_v1.json --profile-sha256 00E0E11553ECD6823AFB07606A00A41C7CEE779A9679555A6D81316FC91BB75D)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_tile_shape.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4We_tile_shape_numeric --num 099 --note 'Preserve prior93877 ERROR9 and exact2e-5/2e-6 tolerance. Same payload/oracle and originalCPU-made scales, two embedding formats x3 row tiles x4 contexts x4 reference-generated positions=96. Diagnose GPU GEMM-shape effect; no quality/tolerance relaxation, no sourceCP load/training or payload edits. Full-row temporary unpack may raise peak. Diagnostic0 is not a quality or oldgate PASS.'
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4We_tile_shape_numeric --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_tile_shape.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4We_tile_shape_numeric --num 099 --note "Final diagnosis exit=$result. Original numeric booleans/exact equality/top1/memory are separate. Prior error stays9 and diagnostic completion does not approve deployment or language quality."
exit "$result"
