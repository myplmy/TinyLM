#!/usr/bin/env bash
# Reuse the owned GPU lock. No overlap with either GSM8K model.
set -uo pipefail
cd /home/uranus/tinyLM || exit 9
python_bin=/home/uranus/miniforge3/envs/tlm_torch/bin/python
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
audit=handoff/audit/nov01_independent
tl_falcon_deadline=$(date -u -d '2026-11-01 02:00:00 UTC' +%s) || exit 9
tl_wait=$((tl_falcon_deadline - $(date -u +%s) - 900))
(( tl_wait > 0 )) || exit 8
exec 9> "$audit/MMLU_NVML_REMAINING.lock"
flock -w "$tl_wait" 9 || exit 8
"$python_bin" -B -c 'import json,pathlib
root=pathlib.Path("test_result/evidence/p106b_gsm8k_nvml_v1_20261101")
for model in ("native595-q","new595-broad-q"):
 for phase in ("cost","full"):
  folder=root/model/phase
  if phase=="full" and not folder.exists():continue
  d=json.loads((folder/"report.json").read_text())
  assert d["final_exit"]==0 and d["source_unchanged"] and d["parent_unchanged"]
  assert not d["final_verification_errors"] and d["vram_watch"]["reason"] is None
  assert d["final_cuda_cleanup"]["allocated_bytes"]==d["final_cuda_cleanup"]["reserved_bytes"]==0
print("Existing GSM8K phases are closed; absent full phases remain NOT_RUN.")' || exit 8

for tl_pair in 'Wc falcon0' 'Wd falcon5'; do
    read -r tl_suffix tl_arm <<< "$tl_pair"
    tl_remaining=$((tl_falcon_deadline - $(date -u +%s) - 120))
    if (( tl_remaining < 800 )); then
        echo "[NOT_RUN] ${tl_arm} cost/full: deadline reserve."
        continue
    fi
    for tl_phase in cost full; do
        tl_remaining=$((tl_falcon_deadline - $(date -u +%s) - 120))
        if [[ "$tl_phase" == full ]]; then
            "$eval_python" -B -X utf8 scripts/diag_p106b_falcon_mmlu.py --mode full --arm "$tl_arm" --profile data_cache/p106b_falcon_mmlu_v3_20261101/profile.json --profile-sha256 7C1CBADC22F5BF76F604FCE668D82A651CC5BFD1D6DD49D60025B83E981947D7 --check-only
            tl_rc=$?
            if (( tl_rc == 8 )); then
                echo "[NOT_RUN] ${tl_arm} full: measured forecast/deadline."
                continue
            fi
            (( tl_rc == 0 )) || exit "$tl_rc"
            tl_stage=14c;tl_limit=5640
        else
            tl_stage=14b;tl_limit=840
        fi
        (( tl_limit > tl_remaining )) && tl_limit=$tl_remaining
        tl_name="P106B_Stage${tl_stage}${tl_suffix}_mmlu_${tl_arm}_${tl_phase}"
        tl_stdout="$audit/${tl_name}_controller_stdout_v1.log"
        [[ ! -e "$tl_stdout" ]] || exit 9
        timeout --signal=TERM --kill-after=20s "${tl_limit}s" "./run_${tl_name}.sh" > "$tl_stdout" 2>&1
        tl_rc=$?
        "$python_bin" -B -c 'import json,sys;print(json.dumps(dict(name=sys.argv[1],actual_exit=int(sys.argv[2]),stdout=sys.argv[3])))' "$tl_name" "$tl_rc" "$tl_stdout"
        (( tl_rc == 0 )) || exit "$tl_rc"
        "$python_bin" -B -c 'import json,pathlib,sys
shot=sys.argv[1][-1]
p=pathlib.Path("test_result/evidence/p106b_falcon_mmlu_v3_20261101")/("shot"+shot)/sys.argv[2]/"report.json"
d=json.loads(p.read_text());proof=d["model_proof"]
assert d["final_exit"]==0 and d["source_unchanged"] and d["assets_unchanged"]
assert proof["initial_core_sha256"]==proof["final_core_sha256"] and proof["source_assets_unchanged"]
assert not d["final_verification_errors"] and d["vram_watch"]["reason"] is None
assert d["final_cuda_cleanup"]["allocated_bytes"]==d["final_cuda_cleanup"]["reserved_bytes"]==0
print(json.dumps(dict(closed=True,shot=int(shot),phase=sys.argv[2],rows=d["actual_rows"])))' "$tl_arm" "$tl_phase" || exit 9
    done
done
"$python_bin" -B -c 'import json,pathlib,datetime
root=pathlib.Path("test_result/evidence/p106b_falcon_mmlu_v3_20261101")
rows=[]
for shot in (0,5):
 for phase in ("cost","full"):
  p=root/("shot"+str(shot))/phase/"report.json"
  d=json.loads(p.read_text()) if p.exists() else {}
  rows.append(dict(shots=shot,phase=phase,status=d.get("status","NOT_RUN"),actual_rows=d.get("actual_rows",0),actual_exit=d.get("final_exit")))
complete=all(r["actual_exit"]==0 for r in rows)
d=dict(status="ALL_FOUR_PHASES_CLOSED" if complete else "PARTIAL_WITH_NOT_RUN",phases=rows,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),quality_pass_claim=False)
p=pathlib.Path("handoff/audit/nov01_independent/FALCON_QUEUE_RECEIPT_v2.json")
with p.open("x") as f:json.dump(d,f,indent=2)
print(json.dumps(d))'
