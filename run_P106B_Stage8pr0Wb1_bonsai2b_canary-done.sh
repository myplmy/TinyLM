#!/usr/bin/env bash
# User158 until17Nov17KST; owned offline existing2B raw-likelihood canary.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export PYTHONIOENCODING=utf-8 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export CUDA_CACHE_DISABLE=1 HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_bonsai2b_prism_canary check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pr0Wb1_bonsai2b_canary --note 'Current158: exact existing Bonsai2B PTQ1 GGUF/Prism adfffbe offline localhost raw-likelihood gate after CPU10+5. Full nativeV distribution, fixed ranks0/7/Vmid forced raw logprobs, B-interposed A state isolation. Whole context reprocessed; original source/model hashes preserved. Single owned server/GPU; no training/install/download/new environment. Phase1200s;cutoff16:40KST. STOP=test_result/evidence/p106b_bonsai2b_prism_canary_v1_20261117/STOP. Exit8=protocol HOLD;1=error;9=closure error;no automatic retry.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pr0Wb1_bonsai2b_canary -- timeout --signal=INT --kill-after=30s 1200s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_bonsai2b_prism_canary actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8pr0Wb1_bonsai2b_canary --note "Actual shell exit=$result. Raw likelihood admission only;formal benchmarks and whole continuation/EOS contracts are separate. Preserve negative and closure evidence."
exit "$result"
