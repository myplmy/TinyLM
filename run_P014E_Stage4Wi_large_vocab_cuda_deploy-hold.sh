#!/usr/bin/env bash
# Independent GPU packed-only counterpart; CPU failure does not block this lane.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--mode deploy-cuda --max-wall-sec 1800 --profile handoff/audit/oct27_independent/large_vocab_deploy_profile_v4.json --profile-sha256 51DBB33A76F6337F8BD85935FACCB6D925689F2560BA3A0F63154AFE232DE0A0)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_deploy.py "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wi_large_vocab_cuda_deploy --num 099 --note 'GPU2 packed-only admitted from same-source export/CUDAreference; CPU lane independent. OriginalCPU scales/body4096/head1024, full4contexts16x3/natural32 and original numeric criterion. Exact allocated/reserved/RSS/KV and original-answer errors separate. New1800s cap/idle4GiB admission/before27Oct17KST. No originalCP tensor reload/new300M/training/data cleanup/install/download.'
timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wi_large_vocab_cuda_deploy --num 099 -- "$python_bin" -B -X utf8 scripts/diag_p014e_large_vocab_deploy.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage4Wi_large_vocab_cuda_deploy --num 099 --note "Final CUDA packed-only exit=$result. Preserve numeric/error/HOLD and cleanup; no quality/whole40MiB or causal acceleration adoption."
exit "$result"
