#!/usr/bin/env bash
# User158; one new full128 DWA block for row-detail storage closure only.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export PYTHONIOENCODING=utf-8 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_CACHE_DISABLE=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export TRITON_CACHE_DIR="$PWD/test_result/evidence/p106b_dwa_native_v3_20261117_s1337/runtime_cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$PWD/test_result/evidence/p106b_dwa_native_v3_20261117_s1337/runtime_cache/inductor"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_dwa_native_v3 check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wd1_native_detail_v3 --note 'User158: original v2 ABBA4 actual0/source/results unchanged. Its per-row rows list was overwritten by integer accounting;original detail unrecoverable. New v3 after storage2/native5/inherited CMA12 executes exactly one full128 DWA block with per-row write-through and separate rows_count. Original student772/teacher811, same seeded projectors/native math and all161 gradient hashes must match original DWA. Teacher body/optimizer/CP write0;not another ABBA and no quality/cost replacement. Same1920s/8GiB/cutoff16:40KST/owned cleanup. STOP=test_result/evidence/p106b_dwa_native_v3_20261117_s1337/STOP.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wd1_native_detail_v3 -- timeout --signal=INT --kill-after=60s 1920s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_dwa_native_v3 actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wd1_native_detail_v3 --note "Actual shell exit=$result. New full128 per-row details belong only to v3;compare exact original161 gradients and full source/state/CUDA closure. Original v2 actual0/aggregates and missing row details are preserved."
exit "$result"
