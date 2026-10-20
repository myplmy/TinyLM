#!/usr/bin/env bash
# P106B_Stage4fjWb_native_broad4_float_cost8: native Q/F parents with original Broad2pass schedule repeated as two continuous cycles.
# Same core/Muon/L0/clip1/micro8 accum16; no old source mutation, downloads, stdin or semantic auto-PASS.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
idle_proof="${1:-handoff/audit/p106b_native_broad4_v1_s1337/idle_float.json}"
if [[ $# -gt 1 || "$idle_proof" != "handoff/audit/p106b_native_broad4_v1_s1337/idle_float.json" ]]; then
    printf '%s\n' '[HOLD] Only the exact own-tag route idle proof is accepted; no path is inspected.' >&2
    exit 8
fi
for proof_path in handoff handoff/audit handoff/audit/p106b_native_broad4_v1_s1337 "$idle_proof"; do
    if [[ -L "$proof_path" ]]; then
        printf '%s\n' '[HOLD] Symlink proof paths are refused before file lookup.' >&2
        exit 8
    fi
done
if [[ ! -f "$idle_proof" ]]; then
    printf '%s\n' '[HOLD] Fresh own-tag root idle proof is required; no stdin is read.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fjWb_native_broad4_float_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fjWb_native_broad4_float_cost8_"$run_stamp" --num 101 --note 'Original22528 rows/nativeQF parents; two continuous cycles704/four passes. New5632 disjoint native windows with original2816 prefix. Actual-worker14400/eval1200/record600, absolute21st17KST/train14KST. Strict activity then readonly VERIFY for training/cost. Root cost idle evidence is tag/route/code-bound. Current mode cost; worker cap900s. Technical completion is not quality. Each public file below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fjWb_native_broad4_float_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_broad4.py --mode cost --arm float --max-wall-sec 900 --execute --idle-proof "$idle_proof"
