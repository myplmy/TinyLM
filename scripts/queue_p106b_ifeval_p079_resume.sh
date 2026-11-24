#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
previous=test_result/101_log_20261120_P106B_WIP48_IFEvalP079Context_GPU.txt
resume=test_result/101_log_20261120_P106B_WIP48_IFEvalP079Context_Resume_GPU.txt
evidence=test_result/evidence/p106b_ifeval_p079_runtime1280_v1_20261120
wait_end=$(( $(date +%s) + 3600 ))

echo "IFEVAL_RESUME_QUEUED $(date '+%F %T') KST"
while [[ ! -e "$evidence/STOP" && $(date +%s) -lt $wait_end ]]; do
    footer=$(tail -n 1 -- "$previous")
    case "$footer" in
        "END "*" status=0"|"END "*" exit=0"|"END "*" actual_exit=0") break ;;
        "END "*) echo "IFEVAL_RESUME_HELD prior worker exit"; exit 2 ;;
    esac
    sleep 10
done
if [[ -e "$evidence/STOP" ]]; then
    echo "IFEVAL_RESUME_HELD stop marker"
    exit 0
fi
if [[ $(date +%s) -ge $wait_end ]]; then
    echo "IFEVAL_RESUME_HELD missing terminal evidence within one hour"
    exit 2
fi

decision=$(python3 -B - "$evidence" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
windows = list(root.glob("window_*.json"))
if len(windows) != 1 or windows[0].is_symlink():
    raise SystemExit("Expected exactly the first terminal window receipt")
receipt = json.loads(windows[0].read_bytes())
profile = hashlib.sha256((root / "profile.json").read_bytes()).hexdigest().upper()
if (receipt["tag"] != root.name or receipt["profile_sha256"] != profile
        or not receipt["state_restored"] or receipt["checkpoint_writes"] != 0):
    raise SystemExit("First window receipt differs from the sealed worker")
if receipt["full_response_count"] and receipt["verified_rows"] == 541:
    print("COMPLETE")
elif (receipt["stop_reason"] == "Window, deadline or stop marker"
      and 0 < receipt["verified_rows"] < 541):
    print("RESUME")
else:
    raise SystemExit("First window did not end on a verified partial time boundary")
PY
)
if [[ "$decision" == COMPLETE || -e "$evidence/STOP" ]]; then
    echo "IFEVAL_RESUME_SKIPPED $decision"
    exit 0
fi
if [[ "$decision" != RESUME ]]; then
    exit 2
fi

set -o noclobber
(
    echo "START $(date '+%F %T') KST"
    set +e
    timeout 3600s env CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
        PYTORCH_CUDA_ALLOC_CONF=expandable_segments:False HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
        /home/uranus/miniforge3/envs/tlm_torch/bin/python -B -m scripts.diag_p106b_ifeval_p079_runtime run
    result=$?
    echo "END $(date '+%F %T') KST status=$result"
    exit "$result"
) > "$resume" 2>&1
