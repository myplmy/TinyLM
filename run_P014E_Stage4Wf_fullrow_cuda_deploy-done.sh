#!/usr/bin/env bash
# Same two payloads and same CUDA reference; whole output rows only.
# Prior128 numerical ERROR9 remains. This is technical, not quality adoption.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode fullrow-cuda --max-wall-sec 1200 --profile handoff/audit/oct27_independent/packed_fullrow_profile_v2.json --profile-sha256 E1509EFC21AFC52B3B4682A480BC585184E4536E302098E5EE44A879C1506DD0)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_fullrow_deploy.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wf_fullrow_cuda_deploy --num 099 --note 'Prior Stage4We69489/0 found exact whole-row16 positions per format; old128 ERROR93877/9 stays. Same files/sourceCPU scales/reference/tolerance,4 workloads/fixed16 warm1 repeat3 observed1/natural32. Tile4096 only. New output, no sourceCP load/reexport/training/new300M. File/held storage/peak/KV/speed/actual answers separate; no quality or40MiB total-runtime adoption.'
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wf_fullrow_cuda_deploy --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_fullrow_deploy.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wf_fullrow_cuda_deploy --num 099 --note "Final full-row exit=$result. Completion0 requires two full suites with numeric/ID/stop/cleanup correspondence. Hold8/error9 preserve partial records. Old failures remain and language quality is not adopted."
exit "$result"
