#!/usr/bin/env bash
# P014D Stage1W: build/test the opt-in native CPU LUT v0, benchmark TinyLM
# shapes, then run the same-session end-to-end model decode gate. Training 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
export TORCH_EXTENSIONS_DIR="${TORCH_EXTENSIONS_DIR:-$repo_root/HF/torch_extensions}"
mkdir -p "$TORCH_EXTENSIONS_DIR"
"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1W_native_lut_kernel \
  --note "P014D Stage1W: opt-in native CPU 5-trit LUT v0 correctness, synthetic shape timing, and actual-model decode speed gate; training 0" \
  || exit $?
"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1W_native_lut_kernel -- \
  "$python_bin" scripts/test_lut_cpu_native.py --compile || exit $?
"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1W_native_lut_kernel -- \
  "$python_bin" scripts/bench_lut_cpu_native.py --threads 1 --warmup 3 --iters 10 \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 069 --name P014D_Stage1W_native_lut_kernel -- \
  "$python_bin" scripts/bench_lut_cpu_model.py --preset m100R1c --data ko-en \
  --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 --max-new 32 \
  --threads 1 --warmup 2 --iters 3 --min-speedup 1.50
