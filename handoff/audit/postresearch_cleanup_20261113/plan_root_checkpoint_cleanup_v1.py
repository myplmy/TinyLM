"""보호·로그 계보와 현재 소스 참조를 대조한다. 삭제/모델 로딩은 하지 않는다."""
from pathlib import Path
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    spec = importlib.util.spec_from_file_location("checkpoint_cleanup", ROOT / "scripts/cleanup_ckpt.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    derived = module.derived_protection()
    archive = load("handoff/audit/checkpoint_retention_20261105_v1/PLAN_v1.json")
    print("old_plan_keys", list(archive))
    print("old_plan_summary", str(archive)[:1800])
    scope = load("handoff/audit/checkpoint_retention_20261105_v1/APPROVED_SCOPE_v1.json")
    print("p107", scope["p107"])
    rows = load("handoff/audit/postresearch_cleanup_20261113/CKPT_INVENTORY_BEFORE_v1.json")["root"]
    files = {Path(row["path"]).name for row in rows}
    candidates = [row for row in rows if row["verdict"] == "hold" and re.search(r"_epoch[123]\.pt$", row["path"])]
    source_paths = sorted((ROOT / "scripts").glob("*.py"))
    source_paths += sorted((ROOT / "tinylm").rglob("*.py"))
    source_paths += [p for p in ROOT.glob("*.sh") if not any(t in p.stem for t in ("-done", "-cancel", "-hold"))]
    source_paths += [p for p in ROOT.glob("*.bat") if not any(t in p.stem for t in ("-done", "-cancel", "-hold"))]
    references = {Path(row["path"]).name: [] for row in candidates}
    for path in source_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name in references:
            if name in text:
                references[name].append(str(path.relative_to(ROOT)))
    planned = []
    for row in candidates:
        name = Path(row["path"]).name
        final = re.sub(r"_epoch[123]\.pt$", ".pt", name)
        checks = dict(final_present=final in files, parent_reference=derived.get(name),
                      source_references=references[name], regular_single_link=not row["symlink"] and row["links"] == 1)
        eligible = checks["final_present"] and not checks["parent_reference"] and not checks["source_references"] and checks["regular_single_link"]
        planned.append(dict(**row, final=final, checks=checks, eligible=eligible))
    result = dict(schema="NOV13_ROOT_INTERMEDIATE_PLAN_V1", candidates=planned,
                  source_files_checked=len(source_paths), protected_derived=list(derived),
                  note="현재 hold 중간 epoch만. 보호39/P107 대조·소비 역할 판독 전 삭제하지 않음.")
    with (OUT / "ROOT_INTERMEDIATE_PLAN_v1.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    for row in planned:
        print("ELIGIBLE" if row["eligible"] else "HOLD", row["path"], row["checks"])
    print("candidate_count", len(planned), "eligible", sum(r["eligible"] for r in planned))


if __name__ == "__main__":
    main()
