#!/usr/bin/env bash
# P087 Stage3bW: evaluate existing checkpoints only; training/download 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 073 --name P087_Stage3bW_paired_fullval   --note "P087 Stage3bW: existing 300M-checkpoint pair on deterministic ko-en 600M-pool val; no training; match train_repeat"   || exit $?
exec "$python_bin" scripts/runlog.py --num 073 --name P087_Stage3bW_paired_fullval --   "$python_bin" scripts/paired_eval.py     --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M     --models d12_cla2_r20_p6_t1200 d12_cla2_r20     --match-train-repeat --dump-crops runs/logs/p087_stage3b_fullval.json
