#!/usr/bin/env bash
# Same owned GPU lock as MMLU. No model opens until all four recovery phases close.
set -uo pipefail
cd /home/uranus/tinyLM || exit 9
python_bin=/home/uranus/miniforge3/envs/tlm_torch/bin/python
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
audit=handoff/audit/nov01_independent
tl_gsm_deadline=$(date -u -d '2026-11-01 02:00:00 UTC' +%s) || exit 9
exec 9> "$audit/MMLU_NVML_REMAINING.lock"
flock -w 7200 9 || exit 8
"$python_bin" -B -c 'import json,pathlib
root=pathlib.Path("test_result/evidence/p106b_mmlu_nvml_v1_20261101")
for model in ("native595-q","new595-broad-q"):
 for phase in ("cost","full"):
  d=json.loads((root/model/"shot5"/phase/"report.json").read_text())
  assert d["final_exit"]==0 and d["source_unchanged"] and d["parent_unchanged"]
  assert d["profile_sha256"]=="98B07574C8AAFAE256E4688D2BA0E4A3F6A133865368937813E460959EA182B5"
  assert not d["final_verification_errors"] and d["vram_watch"]["reason"] is None
  assert d["final_cuda_cleanup"]["allocated_bytes"]==d["final_cuda_cleanup"]["reserved_bytes"]==0
print("MMLU recovery closed; GSM8K can enter fresh cost gate.")' || exit 8

tl_gsm_run() {
    local tl_arm="$1" tl_phase="$2" tl_suffix="$3" tl_limit tl_name tl_stdout tl_rc tl_remaining
    tl_remaining=$((tl_gsm_deadline - $(date -u +%s) - 120))
    (( tl_remaining > 1000 )) || return 8
    if [[ "$tl_phase" == cost ]]; then tl_limit=1100; else tl_limit=11040; fi
    (( tl_limit > tl_remaining )) && tl_limit=$tl_remaining
    tl_name="P106B_Stage8${tl_suffix}_gsm8k_${tl_arm}_${tl_phase}"
    tl_stdout="$audit/${tl_name}_controller_stdout_v1.log"
    [[ ! -e "$tl_stdout" ]] || return 9
    timeout --signal=TERM --kill-after=20s "${tl_limit}s" "./run_${tl_name}.sh" > "$tl_stdout" 2>&1
    tl_rc=$?
    "$python_bin" -B -c 'import json,sys;print(json.dumps(dict(name=sys.argv[1],actual_exit=int(sys.argv[2]),stdout=sys.argv[3])))' "$tl_name" "$tl_rc" "$tl_stdout"
    (( tl_rc == 0 )) || return "$tl_rc"
    "$python_bin" -B -c 'import json,pathlib,sys
model="native595-q" if sys.argv[1]=="native" else "new595-broad-q"
d=json.loads((pathlib.Path("test_result/evidence/p106b_gsm8k_nvml_v1_20261101")/model/sys.argv[2]/"report.json").read_text())
assert d["final_exit"]==0 and d["source_unchanged"] and d["parent_unchanged"] and d["assets_unchanged"]
assert not d["final_verification_errors"] and d["vram_watch"]["reason"] is None
assert d["final_cuda_cleanup"]["allocated_bytes"]==d["final_cuda_cleanup"]["reserved_bytes"]==0
print(json.dumps(dict(phase_closed=True,model=model,phase=sys.argv[2],rows=d["actual_rows"])))' "$tl_arm" "$tl_phase"
}

tl_gsm_run native cost yWa || exit $?
tl_gsm_run broad cost yWb || exit $?
# Resource measurements only decide scheduling. Official test scores do not choose a model.
mapfile -t tl_order < <("$python_bin" -B -c 'import json,pathlib
root=pathlib.Path("test_result/evidence/p106b_gsm8k_nvml_v1_20261101")
costs=[(json.loads((root/model/"cost/report.json").read_text())["generation_seconds"],arm) for arm,model in [("native","native595-q"),("broad","new595-broad-q")]]
for _,arm in sorted(costs):print(arm)')
(( ${#tl_order[@]} == 2 )) || exit 9
for tl_arm in "${tl_order[@]}"; do
    if [[ "$tl_arm" == native ]]; then tl_suffix=zWa; else tl_suffix=zWb; fi
    "$eval_python" -B -X utf8 scripts/diag_p106b_official_gsm8k.py --mode full --arm "$tl_arm" --profile data_cache/p106b_gsm8k_official_v1_20261101/profile_v2.json --profile-sha256 0EFFADD069945BEEE4739F4BCCD5D220D2348119FEA3329DBB1E0659A86A46F9 --check-only
    tl_rc=$?
    if (( tl_rc == 8 )); then
        echo "[NOT_RUN] ${tl_arm} full does not fit measured budget/deadline."
        continue
    fi
    (( tl_rc == 0 )) || exit "$tl_rc"
    tl_gsm_run "$tl_arm" full "$tl_suffix" || exit $?
done
