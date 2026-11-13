"""Verify immutable plan copies against their recorded digest and original link base."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
receipt = json.loads((OUT / "FINAL_STATIC_AUDIT_v2_reads/check_links.json").read_text())
paths = sorted({row["path"] for row in receipt["inputs"]
                if row["path"].endswith("/initial_plan.md")})
assert len(paths) == 7, paths
rows = []
for name in paths:
    path = ROOT / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    profile_path = path.with_name("profile.json")
    profile = json.loads(profile_path.read_text())
    field = "plan_sha256" if "plan_sha256" in profile else "initial_plan_sha256"
    assert profile[field].upper() == digest, name
    links = []
    for raw in re.findall(r"\]\(([^)#][^)]*?)\)", path.read_text()):
        target = raw.split("#")[0].strip()
        if not target or target.startswith(("https://", "http://", "mailto:")):
            continue
        if "{" in target or "..." in target:
            continue
        if not re.search(r"\.(md|txt|py|bat|json|png|pdf|tsv|csv)$", target):
            continue
        original = (ROOT / "test_plan" / target).resolve()
        original_name = original.relative_to(ROOT).as_posix()
        assert not original_name.startswith("datasets/"), original_name
        assert original.is_file(), (name, original_name)
        assert not (path.parent / target).exists(), (name, target)
        links.append(dict(relative_as_original=target, original_base_target=original_name))
    rows.append(dict(snapshot=name, sha256=digest,
        profile=profile_path.relative_to(ROOT).as_posix(), profile_field=field, links=links))
assert sum(len(row["links"]) for row in rows) == 20
value = dict(schema="NOV13_IMMUTABLE_SNAPSHOT_LINK_BASE_V2", snapshots=rows,
    link_count=20, snapshot_count=7, status="ORIGINAL_BASE_VERIFIED",
    note="Raw evidence bytes and shared checker remain unchanged. Scoped live-document checks exclude only these seven SHA-pinned copies; global link checker still sees their relocated links.")
with (OUT / "SNAPSHOT_LINK_BASE_AUDIT_v2.json").open("x", encoding="utf-8") as stream:
    json.dump(value, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps(dict(snapshots=len(rows), links=value["link_count"], status=value["status"])))
