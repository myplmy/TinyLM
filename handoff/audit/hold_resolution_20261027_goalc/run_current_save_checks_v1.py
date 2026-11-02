"""Run the five relevant CPU regression files once and preserve exact output."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
REPORT = AUDIT / "CURRENT_BIRTH_SCOPE_CPU_CHECKS_V1.json"
assert not REPORT.exists()
environment = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1",
                   OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   RAYON_NUM_THREADS="1", TOKENIZERS_PARALLELISM="false")
files = ["test_p106b_hold_resolution_inventory.py",
         "test_p106b_hold_resolution_review_safeguards_v3.py",
         "test_p106b_hold_resolution_preservation_v1.py",
         "test_p106b_hold_resolution_birth_conflicts_v1.py",
         "test_p106b_hold_resolution_author_output_bindings_v1.py"]
rows = []
for name in files:
    argv = [sys.executable, "-I", "-B", str(ROOT / "scripts" / name)]
    log = AUDIT / ("current_save_20261102_" + Path(name).stem + ".log")
    assert not log.exists()
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    with log.open("xb") as stream:
        stream.write(result.stdout)
    output = result.stdout.decode("utf-8", errors="replace")
    match = re.search(r"Ran (\d+) tests?", output)
    rows.append(dict(test=name, argv=argv, exit_code=result.returncode,
        tests=int(match.group(1)) if match else None,
        seconds=time.monotonic() - started, log=str(log.relative_to(ROOT)),
        log_sha256=hashlib.sha256(result.stdout).hexdigest().upper(),
        source_sha256=hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest().upper()))
record = dict(status="ACTUAL_CPU_REGRESSION_RESULTS", rows=rows,
              total_tests=sum(row["tests"] or 0 for row in rows),
              failures=sum(row["exit_code"] != 0 for row in rows),
              GPU_runs=0, model_runs=0)
with REPORT.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(tests=record["total_tests"], failed_suites=record["failures"])))
raise SystemExit(2 if record["failures"] else 0)
