"""Recheck saved scope pins and WIP tests without reopening other work."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
WIP = ROOT / "handoff/WIP_20261027_작업원장.md"
parser = argparse.ArgumentParser()
parser.add_argument("--phase", choices=["pre", "post"], required=True)
args = parser.parse_args()
report_path = AUDIT / ("CURRENT_BIRTH_SCOPE_" + args.phase.upper() + "_CHECKS_V1.json")
log_path = AUDIT / ("current_birth_scope_wip_" + args.phase + "_v1.log")
assert not report_path.exists() and not log_path.exists()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def check(pin):
    path = ROOT / pin["path"]
    assert path.is_file() and not path.is_symlink()
    assert sha(path) == pin["sha256"], pin["path"]
    if "bytes" in pin:
        assert path.stat().st_size == pin["bytes"]


local = read("CURRENT_BIRTH_SCOPE_LOCAL_ARTIFACTS_V1.json")
pins = local["local_data_files"] + local["current_top_level_metadata"]
for row in local["author_md_archives"]:
    pins.extend([row["original"], row["archive"]])
for value in pins:
    check(value)
for name in ["ROOT_NINE_GUARD_SELECTIONS_V1.json", "ROOT_BIRTH_BODY_SELECTIONS_V1.json",
             "BIRTH_AUTHORED_BODY_AUDIT_V2.json"]:
    for path, digest in read(name)["input_pins"].items():
        check(dict(path=path, sha256=digest))
birth = read("ROOT_BIRTH_BODY_SELECTIONS_V1.json")
assert birth["source_ids"] == 753 and birth["occurrences"] == 1135
assert birth["prior_global_selection_superseded"] == birth["cache_admitted"] == 0
before = read("supplemental_candidates_snapshot_v48.json")
after = read("supplemental_candidates_snapshot_v51.json")
assert before["errors"] == after["errors"] and len(after["errors"]) == 26
assert after["invalid_task_rows_skipped"] == before["invalid_task_rows_skipped"] == 5
assert after["coverage"]["birth_field_native_counter_v1"] == dict(
    expected=753, saved=753, awaiting_review=0, explicitly_reassigned=0)
environment = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1",
    OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", RAYON_NUM_THREADS="1",
    TOKENIZERS_PARALLELISM="false")
argv = [sys.executable, "-I", "-B", str(ROOT / "scripts/test_wip.py")]
result = subprocess.run(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
with log_path.open("xb") as stream:
    stream.write(result.stdout)
match = re.search(r"Ran (\d+) tests?", result.stdout.decode("utf-8", errors="replace"))
assert result.returncode == 0 and match and int(match.group(1)) == 31
capsule = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"),
    "--capsule-check", "--file", str(WIP)], cwd=ROOT, env=environment,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
assert capsule.returncode == 0
record = dict(status="CURRENT_SCOPE_PINS_AND_WIP_CHECKS_PASS", phase=args.phase,
    verified_pin_occurrences=len(pins), local_data_files=local["local_data_file_count"],
    new_collection_errors=0, historical_collection_errors_preserved=26,
    historical_invalid_TASK_rows_preserved=5, WIP_tests=31, WIP_exit_code=result.returncode,
    WIP_sha256=sha(WIP), WIP_log=dict(path=str(log_path.relative_to(ROOT)), sha256=sha(log_path)),
    capsule_exit_code=capsule.returncode, capsule_output=capsule.stdout.decode("utf-8", errors="replace"),
    CPU_regressions_other=54, distinct_CPU_regressions=85, isolated_Git_checks=8,
    negative_history_preserved=["snapshot49 mechanical errors8", "body audit1 death conflicts2"],
    save_helper_corrections=["initial cohort selector stopped before output on rows/records key; corrected then exit0",
        "initial WIP wait rejected non-Korean note before mutation; corrected Korean command succeeded"],
    cache_admitted=0, final_cache_created=False, goal_complete=False, training_authorized=False)
with report_path.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps({key: record[key] for key in ["status", "phase", "local_data_files", "distinct_CPU_regressions", "isolated_Git_checks"]}))
