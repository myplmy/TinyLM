#!/usr/bin/env bash
# P104A Stage0W: WSL M4 direct Triton ternary GEMM. About 0.1 h GPU.
# Numeric/support gate only; no training or whole-model speed claim.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage0W_m4_triton_ternary --note "Direct Triton call required. Reference fallback does not count as M4 pass. Read NRMS, cosine and peak allocation separately."
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage0W_m4_triton_ternary -- "$python_bin" -B -X utf8 scripts/diag_m4_triton_ternary.py --m 64 --k 768 --n 768 --group 128 --max-nrms 0.02 --min-cosine 0.999
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[GATE] M4 direct Triton returned rc=$rc; inspect the log before M5" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage0W_m4_triton_ternary --note "M4 Triton function gate passed only for this shape. M4 other backends and M5 real quality remain separate."
