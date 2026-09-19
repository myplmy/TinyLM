#!/usr/bin/env bash
# P076 Stage1: actual parent checkpoint, one fixed val crop, training 0.
# The step0 values are an initialization-validity band, not a ranking.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --name P076_Stage1W_group_init_gate   --note "P076 Stage1W: mean/middle/norm_mean actual-parent step0 validity band; training 0; do not rank final quality"   || exit $?
exec "$python_bin" scripts/runlog.py --name P076_Stage1W_group_init_gate --   "$python_bin" scripts/diag_depth_init.py     --preset m100R1c --teacher-preset m100 --data ko-en --tokens 300M     --seq 512 --bs 2 --device cuda --group-inits mean middle norm_mean
