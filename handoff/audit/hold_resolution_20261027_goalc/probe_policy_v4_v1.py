"""Measure new draft behavior on the saved, already independently read packets."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v4 as policy

BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
AUDIT = Path(__file__).resolve().parent
manifest = BASE / "draft_proposals_v3/review_packets/manifest.json"
packets = json.loads(manifest.read_text())["rows"]
results = []
for row in packets:
    path = ROOT / row["paths"]["original"]["path"]
    text = path.read_text()
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == row["original_text_sha256"]
    value = policy.propose(dict(row, text=text))
    results.append(dict(id=row["id"], old_decision=row["decision"], decision=value["decision"], reasons=value["reasons"],
                        changes=value["changes"], code_preserved=policy.code_preserved(text, value.get("candidate", value["text"]))))
counts = dict(Counter(r["decision"] for r in results))
with (AUDIT / "policy_v4_purpose_probe_v1.json").open("x", encoding="utf-8") as f:
    json.dump(dict(purpose="PURPOSED_SHAPES_NOT_INDEPENDENT_ADMISSION", counts=counts, rows=results), f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(json.dumps(counts))
print([(r["id"],r["decision"],r["reasons"]) for r in results if r["id"] in {"expanded_train:730328","expanded_train:539310","expanded_train:968829","expanded_train:794733","expanded_train:75490","expanded_train:288372"}])
