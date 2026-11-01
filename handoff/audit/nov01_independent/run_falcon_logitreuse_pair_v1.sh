#!/usr/bin/env bash
set -uo pipefail
cd /home/uranus/tinyLM || exit 9
audit=handoff/audit/nov01_independent
exec 9> "$audit/MMLU_NVML_REMAINING.lock"
flock -n 9 || exit 8
for phase in cost full; do
 if [[ "$phase" == cost ]]; then stage=14fWa; else stage=14gWa; fi
 name="P106B_Stage${stage}_mmlu_falcon0_logitreuse_${phase}"
 log="$audit/${name}_controller_stdout_v1.log"
 [[ ! -e "$log" ]] || exit 9
 bash "./run_${name}.sh" > "$log" 2>&1
 code=$?
 /home/uranus/miniforge3/envs/tlm_torch/bin/python -B -c 'import json,sys;print(json.dumps(dict(phase=sys.argv[1],actual_exit=int(sys.argv[2]))))' "$phase" "$code"
 (( code == 0 )) || exit "$code"
done
