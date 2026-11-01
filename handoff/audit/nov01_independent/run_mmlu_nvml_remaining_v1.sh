#!/usr/bin/env bash
# Only four fresh validated NVML MMLU5 cost/full launchers.
# No concurrency/retries. Each launcher retains source/profile/8GB admission.
set -uo pipefail
cd /home/uranus/tinyLM || exit 9
python_bin=/home/uranus/miniforge3/envs/tlm_torch/bin/python
audit=handoff/audit/nov01_independent
exec 9> "$audit/MMLU_NVML_REMAINING.lock"
flock -n 9 || exit 8
tl_mmlu_deadline=$(date -u -d '2026-11-01 02:00:00 UTC' +%s) || exit 9
for tl_pair in 'Wa native5' 'Wb broad5'; do
    read -r tl_suffix tl_arm <<< "$tl_pair"
    for tl_phase in cost full; do
        tl_remaining=$((tl_mmlu_deadline - $(date -u +%s) - 120))
        if (( tl_remaining < 900 )); then
            "$python_bin" -B -c 'import json,sys;print(json.dumps(dict(status="NOT_RUN_DEADLINE_RESERVE",arm=sys.argv[1],phase=sys.argv[2])))' "$tl_arm" "$tl_phase"
            exit 8
        fi
        if [[ "$tl_phase" == cost ]]; then
            tl_stage=13d
            tl_limit=900
        else
            tl_stage=13e
            tl_limit=5640
        fi
        (( tl_limit > tl_remaining )) && tl_limit=$tl_remaining
        tl_name="P106B_Stage${tl_stage}${tl_suffix}_mmlu_nvml_${tl_arm}_${tl_phase}"
        tl_stdout="$audit/${tl_name}_controller_stdout_v1.log"
        [[ ! -e "$tl_stdout" ]] || exit 9
        timeout --signal=TERM --kill-after=20s "${tl_limit}s" "./run_${tl_name}.sh" > "$tl_stdout" 2>&1
        tl_rc=$?
        "$python_bin" -B -c 'import json,sys;print(json.dumps(dict(name=sys.argv[1],actual_exit=int(sys.argv[2]),stdout=sys.argv[3])))' "$tl_name" "$tl_rc" "$tl_stdout"
        if (( tl_rc != 0 )); then
            # Root investigates before any more GPU after an unclosed phase.
            exit "$tl_rc"
        fi
        "$python_bin" -B -c 'import json,sys,pathlib
model="native595-q" if sys.argv[1].startswith("native") else "new595-broad-q"
shot=sys.argv[1][-1]
p=pathlib.Path("test_result/evidence/p106b_mmlu_nvml_v1_20261101")/model/("shot"+shot)/sys.argv[2]/"report.json"
d=json.loads(p.read_text())
assert d["final_exit"]==0 and d["source_unchanged"] and d["parent_unchanged"]
assert not d["final_verification_errors"]
assert d["final_cuda_cleanup"]["allocated_bytes"]==d["final_cuda_cleanup"]["reserved_bytes"]==0
print(json.dumps(dict(phase_closed=True,model=model,shots=int(shot),phase=sys.argv[2],actual_rows=d["actual_rows"])))' "$tl_arm" "$tl_phase" || exit 9
    done
done
