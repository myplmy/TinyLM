#!/usr/bin/env bash
# COMPLETE: closed raw verdict0 and result101 section374 recorded; preserve commands, no automatic rerun.
# P106B_Stage4fiWa_headwise_muon_cost8: one isolated Q/K head-wise NS-unit contrast, not full DeepSeek training.
# Same completed float-native parent and frozen SFT384; old Muon/data/CP/code stay unchanged.
# Actual-worker3600/record600; absolute21st17KST and training14KST. No stdin/download.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
idle_proof="${1:-handoff/audit/WIP_20261020_HEADWISE_COST_IDLE_PROOF.json}"
if [[ $# -gt 1 || "$idle_proof" != "handoff/audit/WIP_20261020_HEADWISE_COST_IDLE_PROOF.json" ]]; then
    printf '%s\n' '[HOLD] Only the exact root audit proof is accepted; no path is inspected.' >&2
    exit 8
fi
for proof_path in handoff handoff/audit "$idle_proof"; do
    if [[ -L "$proof_path" ]]; then
        printf '%s\n' '[HOLD] Symlink proof paths are refused before file lookup.' >&2
        exit 8
    fi
done
if [[ ! -f "$idle_proof" ]]; then
    printf '%s\n' '[HOLD] A fresh root idle-proof JSON is required; no stdin is read.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fiWa_headwise_muon_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fiWa_headwise_muon_cost8_"$run_stamp" --num 101 --note 'Same float native parent, unchanged L0/SFT4passes384/micro8 accum16/clip1/AMP/default compile/RMS/WD0. Q14/K-owner7 NS unit only. Cost8 requires matching UTC and monotonic300s root idle proof, end fresh600s; no continuous peak/OOM claim. No source retag or generic float loader. Execution worker closes activity before readonly strict VERIFY child and final three-phase verdict. Files below20MB. Worker cap900s; technical completion is not answer quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fiWa_headwise_muon_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_headwise_muon.py --mode cost --max-wall-sec 900 --execute --idle-proof "$idle_proof"
