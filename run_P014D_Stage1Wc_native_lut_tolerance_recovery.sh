#!/usr/bin/env bash
# P014D Stage1Wc: rerun v1 after correcting the float32 reduction-order test tolerance.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wc_native_lut_tolerance_recovery --note \
  "P014D Stage1Wc: Stage1Wb stopped at an overly strict 1e-6 synthetic tolerance." \
  "The incremental float32 kernel is now checked at rtol=atol=1e-5; model speed gate remains >=1.50x native/int8."

"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wc_native_lut_tolerance_recovery -- \
  "$python_bin" scripts/test_lut_cpu_native.py --compile || exit $?

"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wc_native_lut_tolerance_recovery -- \
  "$python_bin" scripts/bench_lut_cpu_native.py --threads 1 --warmup 3 --iters 10 || exit $?

exec "$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1Wc_native_lut_tolerance_recovery -- \
  "$python_bin" scripts/bench_lut_cpu_model.py \
    --preset m100R1c --data ko-en --tokens 300M \
    --models mC_cla2_ag4 mC_cla2_ag4_r20 \
    --max-new 32 --threads 1 --warmup 2 --iters 3 --min-speedup 1.50
