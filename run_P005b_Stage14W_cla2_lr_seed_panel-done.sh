#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 078 --name P005b_Stage14W_cla2_lr_seed_panel -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en \
    --tokens 600M --ckpt-tokens 300M \
    --models d14_cla2_norecur_rms4 d14_cla2_norecur_rms4_lr15 \
      d14_cla2_norecur_rms4_lr20 || exit $?
"$python_bin" scripts/runlog.py --num 078 --name P005b_Stage14W_cla2_lr_seed_panel -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en \
    --tokens 600M --ckpt-tokens 300M \
    --models d14_cla2_norecur_rms4_s2024 d14_cla2_norecur_rms4_lr15_s2024 \
      d14_cla2_norecur_rms4_lr20_s2024 || exit $?
exec "$python_bin" scripts/runlog.py --num 078 --name P005b_Stage14W_cla2_lr_seed_panel -- \
  "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en \
    --tokens 600M --ckpt-tokens 300M \
    --models d14_cla2_norecur_rms4_s31415 d14_cla2_norecur_rms4_lr15_s31415 \
      d14_cla2_norecur_rms4_lr20_s31415
