"""Version the existing independent full-draft verifier after observed exit0."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "verify_v20_artifacts_v1.py").read_text(encoding="utf-8")
assert source.count("36526") == 2 and source.count("len(codes) == 46") == 1
source = source.replace("v20", "v21").replace("V20", "V21").replace("36526", "66274")
source = source.replace("len(codes) == 46", "len(codes) == 52")
with (base / "verify_v21_artifacts_v1.py").open("x", encoding="utf-8") as out:
    out.write(source)
