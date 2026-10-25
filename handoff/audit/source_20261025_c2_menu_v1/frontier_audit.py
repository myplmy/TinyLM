#!/usr/bin/env python3
"""Compile every physical experiment plan into one conservative frontier inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_ID_RE = re.compile(r"^(P\d{3}[A-Za-z]?)_")
INDEX_ROW_RE = re.compile(r"^\| \[(P\d{3}[A-Za-z]?)\]\(([^)]+)\) \| (.*?) \| (.*?) \|$")
RESULT_RE = re.compile(r"(?:결과\s*|result[/ _-]?)(\d{3})(?!\d)", re.IGNORECASE)
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
STAGE_RE = re.compile(r"(?i)(?:^#{2,}\s+|^\|\s*\*{0,2})(Stage\s*\w+|단계\s*[\w.-]+)(.*)$")
DONE_MARKERS = ("✅", "완료", "종결", "폐기", "기각")
OPEN_MARKERS = ("⏳", "🔄", "대기", "미실행", "미구현", "NOT_RUN", "실행 전")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest().upper()


def index_rows(root: Path):
    current = None
    rows = {}
    index = root / "test_plan" / "실험계획목록.md"
    for line in index.read_text(encoding="utf-8").splitlines():
        if line == "## 1. 계획만 있고 실행 전":
            current = "PLANNED"
        elif line == "## 2. 진행 중":
            current = "ONGOING"
        elif line == "## 3. 종결":
            current = "DONE"
        match = INDEX_ROW_RE.match(line)
        if match:
            ident, filename, question, current_gate = match.groups()
            rows[ident] = {
                "filename": filename,
                "index_state": current,
                "question": question.strip(),
                "index_gate": current_gate.strip(),
            }
    return rows


def experiment_rows(root: Path):
    result = []
    for line_no, raw in enumerate((root / "experiments.tsv").read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        cells = [cell.strip() for cell in raw.split("\t")]
        if cells[0] == "prio" or len(cells) < 8:
            continue
        batch = cells[2]
        target = root / batch
        suffix = target.suffix
        stem = batch[:-len(suffix)] if suffix else batch
        done = sorted(root.glob(stem + "-done*" + suffix))
        try:
            hours = float(cells[4])
        except ValueError:
            hours = 0.0
        result.append({
            "line": line_no, "plan": cells[1], "batch": batch,
            "gpu": cells[3], "hours": hours, "note": cells[7],
            "exists": target.is_file(), "done": [path.name for path in done],
        })
    return result


def plan_header_state(text: str, filename: str) -> str:
    lines = text.splitlines()[:30]
    status_lines = [
        line for line in lines
        if re.match(r"^\s*(?:[-*>]\s*)?(?:\*\*)?(?:(?:현재 )?상태|이 계획은|계획 전체|전체 상태)", line)
    ]
    explicit = "\n".join(status_lines)
    if filename.endswith("-done.md") or re.search(r"(?:종결|닫힘)", explicit):
        return "DONE"
    if re.search(r"(?:진행 중|일부 완료|실행 대기|HOLD)", explicit):
        return "ONGOING"
    if re.search(r"(?:전체 미착수|상태[:： ]*[^\n]{0,20}실행 전)", explicit):
        return "PLANNED"
    return "UNKNOWN"


def first_unfinished(text: str) -> str:
    candidates = []
    for line in text.splitlines():
        match = STAGE_RE.search(line.strip())
        if not match:
            continue
        normalized = re.sub(r"\s+", " ", line.strip(" |#"))
        candidates.append(normalized)
        if any(marker in normalized for marker in OPEN_MARKERS) and not any(
            marker in normalized for marker in DONE_MARKERS
        ):
            return normalized[:240]
    return candidates[-1][:240] if candidates else "미식별"


def first_prerequisite(text: str, index_gate: str) -> str:
    for line in text.splitlines():
        if "선결" in line and not line.lstrip().startswith("#"):
            return re.sub(r"\s+", " ", line.strip(" |"))[:240]
    return index_gate[:240] if index_gate else "문서에 명시 없음"


def active_review_paths(root: Path):
    review = root / "docs" / "review"
    if not review.is_dir():
        return []
    retired = ("absorbed", "superseded", "integrated", "통합", "폐기")
    return [path for path in sorted(review.glob("*.md")) if not any(x in path.name.lower() for x in retired)]


def compile_frontier(root: Path):
    plans = {}
    for path in sorted((root / "test_plan").glob("P*.md")):
        match = PLAN_ID_RE.match(path.name)
        if match:
            plans[match.group(1)] = path
    index = index_rows(root)
    experiments = experiment_rows(root)
    compass_text = (root / "handoff" / "COMPASS.md").read_text(encoding="utf-8")
    reviews = [(path, path.read_text(encoding="utf-8")) for path in active_review_paths(root)]
    result_paths = sorted((root / "test_result").glob("[0-9][0-9][0-9]_*.md")) if (root / "test_result").is_dir() else []
    result_ids = {int(path.name[:3]) for path in result_paths}
    rows = []
    for ident, path in sorted(plans.items()):
        text = path.read_text(encoding="utf-8")
        idx = index.get(ident, {})
        launchers = [row for row in experiments if row["plan"].upper() == ident.upper()]
        live = [row for row in launchers if row["exists"]]
        # A live historical launcher remains in inventory but is not READY.
        eligible = [row for row in live if not row["note"].lstrip().upper().startswith("HOLD:")]
        done_launchers = [name for row in launchers for name in row["done"]]
        header_state = plan_header_state(text, path.name)
        index_state = idx.get("index_state", "MISSING")
        conflicts = []
        if index_state == "MISSING":
            conflicts.append("physical plan missing from index")
        if header_state != "UNKNOWN" and index_state != "MISSING" and header_state != index_state:
            conflicts.append(f"plan header={header_state} index={index_state}")
        if index_state == "DONE" and live:
            conflicts.append("closed plan still has live launcher")
        if index_state != "DONE" and path.name.endswith("-done.md"):
            conflicts.append("done-suffix plan is not in closed index")
        results = [int(value) for value in RESULT_RE.findall(text)]
        latest_result = max(results) if results else None
        if latest_result is not None and latest_result not in result_ids and result_paths:
            conflicts.append(f"referenced result {latest_result:03d} has no physical document")
        if conflicts:
            readiness = "CONFLICT"
        elif index_state == "DONE":
            readiness = "DONE"
        elif eligible and any(row["gpu"].upper() == "Y" for row in eligible):
            readiness = "READY"
        elif eligible:
            readiness = "GATED"
        else:
            readiness = "HOLD"
        dates = DATE_RE.findall(text)
        compass_axes = []
        for line in compass_text.splitlines():
            if line.startswith("|") and ident in line:
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if cells:
                    compass_axes.append(re.sub(r"[*`]", "", cells[0]))
        review_refs = [path.name for path, body in reviews if re.search(rf"\b{re.escape(ident)}\b", body)]
        rows.append({
            "plan_id": ident,
            "plan_path": path.relative_to(root).as_posix(),
            "whole_state": index_state,
            "plan_header_state": header_state,
            "first_unfinished_stage": first_unfinished(text),
            "latest_result": latest_result,
            "evidence_date": max(dates) if dates else None,
            "launcher_inventory": {
                "live": [item["batch"] for item in live],
                "done": done_launchers,
                "registered": [item["batch"] for item in launchers],
            },
            "preflight_count": len(live),
            "readiness": readiness,
            "first_prerequisite": first_prerequisite(text, idx.get("index_gate", "")),
            "estimated_hours": round(sum(item["hours"] for item in live), 3),
            "compass_axis": sorted(set(compass_axes)),
            "active_review_refs": review_refs,
            "conflicts": conflicts,
            "disposition_required": readiness != "DONE",
        })
    physical = set(plans)
    indexed = set(index)
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_paths = [
        root / "test_plan" / "실험계획목록.md",
        root / "experiments.tsv",
        root / "handoff" / "COMPASS.md",
        *([root / "docs" / "EXPERIMENT_BASELINES.md"] if (root / "docs" / "EXPERIMENT_BASELINES.md").is_file() else []),
        *plans.values(),
        *result_paths,
        *(path for path, _body in reviews),
    ]
    return {
        "schema": "TINYLM_FRONTIER_V1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frontier_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper(),
        "source_manifest": [
            {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
            for path in source_paths
        ],
        "counts": {
            "physical_plans": len(physical), "index_rows": len(indexed),
            "frontier_rows": len(rows),
            "disposition_required": sum(row["disposition_required"] for row in rows),
        },
        "set_differences": {
            "physical_without_index": sorted(physical - indexed),
            "index_without_physical": sorted(indexed - physical),
        },
        "rows": rows,
    }


def render_markdown(data) -> str:
    def plain_cell(value) -> str:
        text = str(value)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = text.replace("`", "").replace("**", "")
        return text.replace("|", "\\|")

    lines = [
        "# TinyLM experiment frontier audit", "",
        f"- schema: `{data['schema']}`",
        f"- frontier SHA-256: `{data['frontier_sha256']}`",
        f"- physical/index/frontier: {data['counts']['physical_plans']}/{data['counts']['index_rows']}/{data['counts']['frontier_rows']}",
        "", "| plan | state | readiness | live launcher | hours | first unfinished | first prerequisite | conflicts |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for row in data["rows"]:
        live = ", ".join(row["launcher_inventory"]["live"]) or "없음"
        conflicts = "; ".join(row["conflicts"]) or "없음"
        cells = [
            row["plan_id"], row["whole_state"], row["readiness"], live,
            f"{row['estimated_hours']:.3f}", row["first_unfinished_stage"],
            row["first_prerequisite"], conflicts,
        ]
        lines.append("| " + " | ".join(plain_cell(cell) for cell in cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check and not args.json_out and not args.md_out:
        print("[frontier] check-only: output files are not written")
    data = compile_frontier(ROOT)
    differences = data["set_differences"]
    errors = len(differences["physical_without_index"]) + len(differences["index_without_physical"])
    if args.json_out:
        target = ROOT / args.json_out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        target = ROOT / args.md_out
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown(data), encoding="utf-8")
    print(
        f"SUMMARY physical={data['counts']['physical_plans']} index={data['counts']['index_rows']} "
        f"frontier={data['counts']['frontier_rows']} dispositions={data['counts']['disposition_required']} "
        f"conflicts={sum(bool(row['conflicts']) for row in data['rows'])} errors={errors} "
        f"sha256={data['frontier_sha256']}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
