#!/usr/bin/env bash
# P106B_Stage4fnWa_native595_broad_ternary_cost8: same frozen22528/four passes704; actual completed Native595 parent only.
# Original SFT math/replay5632/optimizer retained. No assets downloaded, stdin, retag or old overwrite.
# Costs and both pending arms must fit before training; child PASS is not answer quality.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
idle_proof="${1:-handoff/audit/p106b_native595_broad_v1_s1337/idle_ternary.json}"
if [[ $# -gt 1 || "$idle_proof" != "handoff/audit/p106b_native595_broad_v1_s1337/idle_ternary.json" ]]; then
    printf '%s\n' '[HOLD] Own exact fresh idle proof is required; no path is inspected.' >&2
    exit 8
fi
for proof_path in handoff handoff/audit handoff/audit/p106b_native595_broad_v1_s1337 "$idle_proof"; do
    if [[ -L "$proof_path" ]]; then
        printf '%s\n' '[HOLD] Symlink proof paths are refused before file lookup.' >&2
        exit 8
    fi
done
if [[ ! -f "$idle_proof" ]]; then
    printf '%s\n' '[HOLD] Fresh300s complete-code-map proof is absent; no stdin.' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fnWa_native595_broad_ternary_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw is preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fnWa_native595_broad_ternary_cost8_"$run_stamp" --num 101 --note 'Actual595 parent completed4543 only; same Broad22528/4pass704 and old597995000 TRAIN/replay5632. micro8 accum16 seq1024 checkpoint-on/L0/Adam5e-5/Muon2e-4 WD0 clip1/default compile. Parent report and normalized descriptor SHA are separate. Original44 controller/core9 bodies retained; active14400/eval3600/record600, train21st14KST/authority17KST. Both costs and all pending estimates required; no float-only budget fallback. Mode cost cap900s; train cap is bounded but no timing guarantee, current budget rechecked. Closed worker plus readonly verifier required for cost/train. All public files below20MB; source16/max17 history answers are not general3turn proof.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fnWa_native595_broad_ternary_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native595_broad.py --mode cost --arm ternary --max-wall-sec 900 --execute --idle-proof "$idle_proof"
