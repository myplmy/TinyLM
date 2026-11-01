"""Run a new purpose version after the independent record-legend counter."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "probe_policy_v21_v1.py").read_text(encoding="utf-8")
assert source.count('"policy_v21_purpose_probe_v1.json"') == 1
source = source.replace('"policy_v21_purpose_probe_v1.json"', '"policy_v21_purpose_probe_v3.json"')
with (base / "probe_policy_v21_v3.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
