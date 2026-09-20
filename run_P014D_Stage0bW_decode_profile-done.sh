#!/usr/bin/env bash
# Stage0 passed the path label "fp32" as an embedding quantization format and
# produced zero measurements. The tool now uses None for the unquantized arm.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 069 --name P014D_Stage0bW_decode_profile \
  --note "P014D Stage0bW: rerun the corrected fp32/int8/LUT decode profiler; self CPU time attribution only, not tok/s" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 069 --name P014D_Stage0bW_decode_profile -- \
  "$python_bin" scripts/diag_decode_profile.py --preset m100R1c --data ko-en --tokens 300M \
  --models mC_cla2_ag4 mC_cla2_ag4_r20 --max-new 32 --paths fp32 int8 lut
