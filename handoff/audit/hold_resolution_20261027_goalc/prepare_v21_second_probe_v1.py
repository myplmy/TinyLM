"""Retain the semantic negative and create a new post-counter purpose probe."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "probe_policy_v21_v1.py").read_text(encoding="utf-8")
assert source.count('"policy_v21_purpose_probe_v1.json"') == 1
source = source.replace('"policy_v21_purpose_probe_v1.json"', '"policy_v21_purpose_probe_v2.json"')
with (base / "probe_policy_v21_v2.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
