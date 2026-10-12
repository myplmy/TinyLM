#!/usr/bin/env bash
# CPU contract body completed directly by Codex; this runlog wrapper was NOT_RUN.
# P101A opt-in SFT MTP: frozen8M x4epochs, not the legacy M0/E384 gate.
# Mode=contract; arm=scratch_ntp; expected0.03h, max600s; user-only model/GPU.
# micro8 accum16 seq1024 checkpointON compiledefault LR1e-4 MuonRMS4 4e-4.
# CPU contract then corpus; each training arm needs its matching cost report.
# Inference requires a completed trained MTP checkpoint; no stdin/old cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage3aW_sft_mtp_cpu_contract_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3aW_sft_mtp_cpu_contract_"$run_stamp" --num 092 --note 'SFT MTP contract scratch_ntp; frozen8M source/val/hash then matched scratch/parent NTP/MTP arms. Real x and assistant/horizon targets are separate from padding. Learned MTP or CPU contracts are not inference speed/semantic quality PASS. No protected source/download/old overwrite or automatic cleanup.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3aW_sft_mtp_cpu_contract_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_sft_mtp.py --mode contract --arm scratch_ntp --tag p101a_sft_mtp_v1_s1337 --max-wall-sec 600 --execute
