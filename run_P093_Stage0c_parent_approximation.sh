#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
ckpt="runs/ckpt/m100s12_ko-en_300M_d16_cla2_norecur_rms4.pt"
if [[ ! -f "$ckpt" ]]; then
    printf '[STOP] required parent checkpoint is missing: %s\n' "$ckpt" >&2
    exit 2
fi
"$python_bin" scripts/runlog.py --num 086 --name P093_Stage0c_parent_approximation \
  --note "P093 Stage0c: actual dense parent MLP groups approximated by shared mean plus rank 4/8/16 residual; latent-weight and synthetic-activation output NRMS" || exit $?
exec "$python_bin" scripts/runlog.py --num 086 --name P093_Stage0c_parent_approximation -- \
  "$python_bin" scripts/diag_sharing_parent_approx.py --ckpt "$ckpt" --arch dense \
  --device cuda --group 4 --ranks 4,8,16 --samples 128
