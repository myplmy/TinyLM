"""Create a fresh v21 probe while retaining the failed pre-write count check."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "probe_policy_v20_v1.py").read_text(encoding="utf-8")
assert source.count("policy_v20") == 2 and source.count("revision_v20") == 1
source = source.replace("policy_v20", "policy_v21").replace("revision_v20", "revision_v21")
path = base / "probe_policy_v21_v1.py"
with path.open("x", encoding="utf-8") as out:
    out.write(source)
print(path)
