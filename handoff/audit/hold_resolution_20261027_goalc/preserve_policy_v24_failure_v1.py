"""Preserve the observed downstream guard failure before its narrow fix."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
paths = ["scripts/p106b_hold_resolution_policy_v24.py", "scripts/test_p106b_hold_resolution_policy_v24.py"]
pins = {}
for name in paths:
    payload = (ROOT / name).read_bytes()
    out = AUDIT / (Path(name).stem + "_initial_failure_source_v1.py")
    with out.open("xb") as stream:
        stream.write(payload)
    pins[name] = hashlib.sha256(payload).hexdigest().upper()
value = dict(tests=356, actual_exit_code=1, failures=2,
    cause="The new wrapper did not repeat the final partial-quarantine/metadata restriction when an earlier proposer is replaced.",
    failed_source_pins=pins, failed_log_sha256=hashlib.sha256((AUDIT / "test_policy_v24_v1.log").read_bytes()).hexdigest().upper(),
    intended_fix="Retain the existing final source-quarantine guard at the current wrapper as well.",
    cache_admitted=0, goal_complete=False, training_authorized=False)
with (AUDIT / "POLICY_V24_INITIAL_REGRESSION_FAILURE_V1.json").open("x", encoding="utf-8") as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print("Preserved both actual failures and their exact source files.")
