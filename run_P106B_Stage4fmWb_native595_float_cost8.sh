#!/usr/bin/env bash
# P106B_Stage4fmWb_native595_float_cost8: explicit4543 native recipe; old controller and defaults never rebound.
# Same scratch028C46, expanded1191116192 pool/externalVAL3005000; no teacher/MTP/headwise.
# CPU/source, measured cost and budget are prerequisites; no stdin/download/old overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
idle_proof="${1:-handoff/audit/p106b_native595_v1_s1337/idle_float.json}"
if [[ $# -gt 1 || "$idle_proof" != "handoff/audit/p106b_native595_v1_s1337/idle_float.json" ]]; then
    printf '%s\n' '[HOLD] Exact own-tag root idle proof required; no path is inspected.' >&2
    exit 8
fi
for proof_path in handoff handoff/audit handoff/audit/p106b_native595_v1_s1337 "$idle_proof"; do
    if [[ -L "$proof_path" ]]; then
        printf '%s\n' '[HOLD] Symlink proof paths are refused before file lookup.' >&2
        exit 8
    fi
done
if [[ ! -f "$idle_proof" ]]; then
    printf '%s\n' '[HOLD] Fresh complete-code-map root proof is missing; no stdin is read.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fmWb_native595_float_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWb_native595_float_cost8_"$run_stamp" --num 101 --note 'Native595 conditional study:4543x8x16x1024 main targets595460096, pool1191116192/externalVAL3005000/scratch028C46. Native Adam/Muon/WSD/anneal/clip1 retained. Cost8 main1048576 plus separate late8192 backward-only/cache checks; no cost CP or quality claim. Actual-worker43200, train cap18000, native stop21st11:30KST/global train14KST/authority17KST. Followup7200/eval1200/record600 reserved; new measured paired budget and fresh300s full-code-map proof before cost. Stage cost cap900s. All public files below20MB; old source/CP/raw unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fmWb_native595_float_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595.py --mode cost --arm float --max-wall-sec 900 --execute --idle-proof "$idle_proof"
