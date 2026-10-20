#!/usr/bin/env bash
# P106B_Stage4flWb_native_broad4_recovery_float_cost8: new namespace after malformed root idle receipt; numerical experiment unchanged.
# Same native Q/F parents, Broad22528 rows/four passes704; Muon/L0/clip1/micro8 accum16/checkpoint-on.
# CPU/metadata and a successful child are not model quality; old failed evidence remains immutable.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
idle_proof="${1:-handoff/audit/p106b_native_broad4_recovery_v2_s1337/idle_float.json}"
if [[ $# -gt 1 || "$idle_proof" != "handoff/audit/p106b_native_broad4_recovery_v2_s1337/idle_float.json" ]]; then
    printf '%s\n' '[HOLD] Only the exact own-tag route idle proof is accepted; no path is inspected.' >&2
    exit 8
fi
for proof_path in handoff handoff/audit handoff/audit/p106b_native_broad4_recovery_v2_s1337 "$idle_proof"; do
    if [[ -L "$proof_path" ]]; then
        printf '%s\n' '[HOLD] Symlink proof paths are refused before file lookup.' >&2
        exit 8
    fi
done
if [[ ! -f "$idle_proof" ]]; then
    printf '%s\n' '[HOLD] Fresh own-tag root idle proof with complete info code map is required; no stdin is read.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4flWb_native_broad4_recovery_float_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4flWb_native_broad4_recovery_float_cost8_"$run_stamp" --num 101 --note 'Recovery-v2 isolated namespace; old failed proof/activity/source untouched. Same original22528/native QF/704/continuous optimizer; actual-worker14400/eval1200/record600,21st17KST authority/train14KST. No stdin. Root fresh300s UTC/monotonic idle and complete info code-map per cost route; never a single-file SHA. Current cost worker cap900s. Actual train/cost require closed worker then readonly verification. Every public file below20MB; technical completion is not intelligence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4flWb_native_broad4_recovery_float_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_broad4_recovery.py --mode cost --arm float --max-wall-sec 900 --execute --idle-proof "$idle_proof"

