#!/usr/bin/env bash
# P014D Stage1Wb: incremental 243-state table + GIL-release recovery gate.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wb_native_lut_incremental --note \
  "P014D Stage1Wb: v1 base-3 incremental table and GIL release; training 0" \
  "Gate preserves Stage1W shapes and >=1.50x native/int8 threshold."

"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wb_native_lut_incremental -- \
  "$python_bin" scripts/test_lut_cpu_native.py --compile || exit $?

"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wb_native_lut_incremental -- \
  "$python_bin" scripts/bench_lut_cpu_native.py --threads 1 --warmup 3 --iters 10 || exit $?

exec "$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wb_native_lut_incremental -- \
  "$python_bin" scripts/bench_lut_cpu_model.py \
    --preset m100R1c --data ko-en --tokens 300M \
    --models mC_cla2_ag4 mC_cla2_ag4_r20 \
    --max-new 32 --threads 1 --warmup 2 --iters 3 --min-speedup 1.50
