"""삭제계획의 보호39 표시만 바로잡고 P107/원로그의 보존 identity를 추가한다."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import OUT, ROOT, digest, identity, read, save

plan = read("handoff/audit/postresearch_cleanup_20261113/EXACT_CLEANUP_PLAN_v1.json")
old = read("handoff/audit/checkpoint_retention_20261105_v1/PLAN_v1.json")
plan["protected39"] = sorted({Path(r["path"]).name for r in old["preserved"] if r.get("optimizer_fields")})
assert len(plan["protected39"]) == 39
plan["parent_plan_sha256"] = digest(OUT / "EXACT_CLEANUP_PLAN_v1.json")
plan["correction"] = "v1의 보호39 표시가 별도9와 겹치는 행을 뺀30개였다. 실제 삭제 제외 집합은 원래39를 포함했으며 후보는 불변이다."
removed = {r["path"] for r in plan["checkpoints"]}
assert not ({"runs/ckpt/" + name for name in plan["protected39"]} & removed)
assert len({r["path"] for r in plan["preserve_root_metadata"]}) == 339
preserve = {}
for directory in plan["p107"]:
    for path in sorted((ROOT / directory).rglob("*")):
        if path.is_file():
            preserve[str(path.relative_to(ROOT))] = identity(path)
for row in plan["launchers"]:
    for log in row["raw_logs"]:
        preserve[log["path"]] = identity(ROOT / log["path"])
for source in ("SYNTHETIC_PROVENANCE_v1.json", "LAUNCHER_FULLTEXT_v1.json"):
    preserve[str((OUT / source).relative_to(ROOT))] = identity(OUT / source)
plan["preserve_exact_identities"] = preserve
save("EXACT_CLEANUP_PLAN_v2.json", plan)
print("plan", digest(OUT / "EXACT_CLEANUP_PLAN_v2.json"), "checkpoints", len(plan["checkpoints"]),
      "launchers", len(plan["launchers"]), "protected", len(plan["protected39"]), "preserve", len(preserve))
for row in plan["launcher_holds"]:
    print("launcher_HOLD", row["path"], row["reason"])
