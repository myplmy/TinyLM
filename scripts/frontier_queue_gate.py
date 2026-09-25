#!/usr/bin/env python3
"""Fail-closed frontier evidence for a finalized handoff experiment queue.

The prepare action creates one reusable artifact per frontier/source/queue signature.
It never chooses a live experiment: every live-plan decision starts as
REVIEW_REQUIRED. Plans without a live launcher are machine-labeled HOLD with
AUTO_NO_LAUNCHER, which is an inventory fact, not a scientific priority review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from frontier_audit import compile_frontier, experiment_rows
from handoff_queue import QUEUE_COLUMNS, _section, _tables


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "TINYLM_FRONTIER_QUEUE_V1"
MARKER = re.compile(
    r"<!-- TINYLM_FRONTIER_QUEUE_V1 artifact=(audit/FRONTIER_QUEUE_[0-9A-F]{12}_[0-9A-F]{12}\.json) "
    r"sha256=([0-9A-F]{64}) -->"
)
DECISIONS = {"INCLUDE", "EXCLUDE", "HOLD"}


def _json_hash(value) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest().upper()


def scoped_handoff(root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    target = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if path.is_symlink() or not target.is_relative_to((root / "handoff").resolve()):
        raise ValueError("handoff must be a non-symlink file under handoff/")
    if not target.is_file() or not re.fullmatch(r"\d{12}_HANDOFF\.md", target.name):
        raise ValueError("handoff must be an existing clock-named file")
    return target


def queue_rows(handoff: Path) -> list[dict]:
    section = _section(handoff.read_text(encoding="utf-8"))
    table = next(
        ((header, rows) for header, rows in _tables(section)
         if all(column in header for column in QUEUE_COLUMNS)),
        None,
    )
    if table is None:
        raise ValueError("handoff §7 has no ten-column queue table")
    header, rows = table
    output = []
    for row in rows:
        batch = row[header.index("배치 파일")].strip(" `")
        if not batch.lower().endswith((".bat", ".sh")):
            continue
        inventory = row[header.index("인벤토리")].strip(" `")
        execution = row[header.index("실행상태")].strip(" `")
        if inventory == "UNVERIFIED":
            raise ValueError("active queue lock: frontier/launcher inventory must not be read")
        if execution == "REVALIDATE":
            raise ValueError(f"§7 has unreviewed inherited row: {batch}")
        if ((inventory == "PRESENT" and execution not in {"READY", "GATED", "HOLD"})
                or (inventory != "PRESENT" and execution != "HOLD")):
            raise ValueError(f"§7 has invalid inventory/execution pair: {batch} {inventory}/{execution}")
        try:
            hours = float(row[header.index("⚙")].strip(" `⚙h시간"))
            raw_id = row[header.index("id")].strip(" `")
            menu_id = int(raw_id) if inventory == "PRESENT" else raw_id
        except ValueError as exc:
            raise ValueError(f"§7 has invalid id/hours for {batch}") from exc
        if hours < 0:
            raise ValueError(f"§7 has negative hours for {batch}")
        output.append({"batch": batch, "id": menu_id, "hours": hours,
                       "inventory": inventory, "execution": execution})
    if len({row["batch"] for row in output}) != len(output):
        raise ValueError("§7 repeats a live batch")
    return output


def _menu_ids(root: Path) -> dict[str, int]:
    """WSL menu ordering: priority then TSV line, present BAT+SH or native SH."""
    items = []
    for line_number, raw in enumerate((root / "experiments.tsv").read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        cells = raw.split("\t")
        if cells[0] == "prio" or len(cells) < 8:
            continue
        batch = cells[2].strip()
        shell = batch[:-4] + ".sh" if batch.lower().endswith(".bat") else batch
        if (root / batch).is_file() and (root / shell).is_file():
            try:
                items.append((int(cells[0]), line_number, shell))
            except ValueError as exc:
                raise ValueError(f"TSV invalid priority at line {line_number}") from exc
    items.sort()
    return {batch: index for index, (_prio, _line, batch) in enumerate(items)}


def _frontier(root: Path) -> dict:
    data = compile_frontier(root)
    counts = data["counts"]
    differences = data["set_differences"]
    if (counts["physical_plans"] != counts["index_rows"]
            or counts["physical_plans"] != counts["frontier_rows"]
            or any(differences.values())):
        raise ValueError("physical plan/index/frontier sets differ")
    conflicts = [row["plan_id"] for row in data["rows"] if row["conflicts"]]
    if conflicts:
        raise ValueError("frontier has conflict rows: " + ",".join(conflicts))
    return data


def artifact_name(frontier: dict, queue: list[dict]) -> str:
    # Plan/result wording can change without altering compiled frontier rows. Bind
    # the full source manifest as well as the queue so immutable evidence is not
    # silently reused with stale input hashes.
    source_queue = _json_hash({"source_manifest": frontier["source_manifest"],
                               "queue_rows": queue})
    return f"FRONTIER_QUEUE_{frontier['frontier_sha256'][:12]}_{source_queue[:12]}.json"


def prepare(root: Path, handoff: Path) -> tuple[Path, dict, bool]:
    frontier = _frontier(root)
    queue = queue_rows(handoff)
    target = root / "handoff" / "audit" / artifact_name(frontier, queue)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise ValueError("frontier artifact path is not a regular file")
        return target, frontier, False
    dispositions = []
    for row in frontier["rows"]:
        if not row["disposition_required"]:
            continue
        live = row["launcher_inventory"]["live"]
        if live:
            decision, reason, review = "REVIEW_REQUIRED", "", "MANUAL_REQUIRED"
        else:
            decision, review = "HOLD", "AUTO_NO_LAUNCHER"
            reason = "등록된 실물 런처 0건; 첫 선결: " + row["first_prerequisite"]
        dispositions.append({"plan_id": row["plan_id"], "decision": decision,
                             "reason": reason, "review": review, "approval_ref": ""})
    document = {"schema": SCHEMA, "frontier_sha256": frontier["frontier_sha256"],
                "source_manifest": frontier["source_manifest"],
                "frontier_rows": frontier["rows"], "queue_sha256": _json_hash(queue),
                "queue_rows": queue, "dispositions": dispositions}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return target, frontier, True


def marker(target: Path, frontier: dict) -> str:
    return (f"<!-- TINYLM_FRONTIER_QUEUE_V1 artifact=audit/{target.name} "
            f"sha256={frontier['frontier_sha256']} -->")


def verify_handoff(root: Path, handoff: Path) -> list[str]:
    errors = []
    try:
        text = handoff.read_text(encoding="utf-8")
        marks = MARKER.findall(_section(text))
        if len(marks) != 1:
            return ["handoff needs exactly one current frontier artifact/SHA marker"]
        relative, stated_sha = marks[0]
        frontier = _frontier(root)
        queue = queue_rows(handoff)
        expected_name = artifact_name(frontier, queue)
        if relative != "audit/" + expected_name:
            errors.append("frontier artifact name is stale for current source/queue")
        if stated_sha != frontier["frontier_sha256"]:
            errors.append("handoff frontier SHA is stale")
        artifact = root / "handoff" / relative
        if artifact.is_symlink() or not artifact.is_file():
            return errors + ["frontier artifact absent or symlinked"]
        data = json.loads(artifact.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            errors.append("frontier artifact schema mismatch")
        if data.get("frontier_sha256") != frontier["frontier_sha256"]:
            errors.append("frontier artifact SHA mismatch")
        if data.get("source_manifest") != frontier["source_manifest"]:
            errors.append("frontier source manifest is stale")
        if data.get("queue_sha256") != _json_hash(queue) or data.get("queue_rows") != queue:
            errors.append("frontier queue signature is stale")
        current = {row["plan_id"]: row for row in frontier["rows"]}
        expected = {ident for ident, row in current.items() if row["disposition_required"]}
        dispositions = data.get("dispositions")
        if not isinstance(dispositions, list):
            return errors + ["frontier dispositions missing"]
        ids = [entry.get("plan_id") for entry in dispositions if isinstance(entry, dict)]
        if len(ids) != len(dispositions) or len(ids) != len(set(ids)) or set(ids) != expected:
            errors.append("frontier non-DONE disposition IDs are missing, duplicated or extra")
        registered = {}
        for row in experiment_rows(root):
            if not row["exists"]:
                continue
            registered[row["batch"]] = row
            shell = row["batch"][:-4] + ".sh" if row["batch"].lower().endswith(".bat") else row["batch"]
            if (root / shell).is_file():
                registered[shell] = row
        menu_ids = _menu_ids(root)
        queued_plans = set()
        held_plans = set()
        for entry in queue:
            if entry["execution"] == "HOLD" and entry["inventory"] != "PRESENT":
                continue
            raw = registered.get(entry["batch"])
            if raw is None or raw["plan"] not in current:
                errors.append(f"queue batch is absent/unmapped: {entry['batch']}")
                continue
            (held_plans if entry["execution"] == "HOLD" else queued_plans).add(raw["plan"])
            if abs(float(raw["hours"]) - entry["hours"]) > 1e-9:
                errors.append(f"queue hours differ from TSV: {entry['batch']}")
            if menu_ids.get(entry["batch"]) != entry["id"]:
                errors.append(f"queue menu id differs: {entry['batch']}")
        for entry in dispositions:
            if not isinstance(entry, dict) or entry.get("plan_id") not in current:
                continue
            ident = entry["plan_id"]
            decision, review = entry.get("decision"), entry.get("review")
            reason = str(entry.get("reason") or "").strip()
            live = current[ident]["launcher_inventory"]["live"]
            if decision not in DECISIONS or len(reason) < 8:
                errors.append(f"{ident}: decision/reason not reviewed")
            if review == "AUTO_NO_LAUNCHER":
                if live or decision != "HOLD":
                    errors.append(f"{ident}: auto HOLD requires zero live launchers")
            elif review != "MANUAL":
                errors.append(f"{ident}: live-plan disposition needs MANUAL review")
            if ident in queued_plans and decision != "INCLUDE":
                errors.append(f"{ident}: selected §7 plan needs INCLUDE")
            elif ident in held_plans and ident not in queued_plans and decision != "HOLD":
                errors.append(f"{ident}: §7 HOLD plan needs HOLD disposition")
            elif ident not in queued_plans and decision == "INCLUDE":
                errors.append(f"{ident}: INCLUDE decision has no runnable §7 row")
            if current[ident]["readiness"] == "READY" and decision != "INCLUDE":
                if not str(entry.get("approval_ref") or "").strip():
                    errors.append(f"{ident}: omitted READY plan needs user approval reference")
        return errors
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return errors + [f"frontier queue gate error: {type(exc).__name__}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--handoff", required=True)
    args = parser.parse_args()
    try:
        handoff = scoped_handoff(ROOT, args.handoff)
        if args.prepare:
            target, frontier, created = prepare(ROOT, handoff)
            print(f"FRONTIER_PREPARED path={target.relative_to(ROOT)} created={int(created)} "
                  f"non_done={frontier['counts']['disposition_required']}")
            print(marker(target, frontier))
            return 0
        errors = verify_handoff(ROOT, handoff)
        for error in errors:
            print("FRONTIER_FAIL " + error)
        print(f"FRONTIER_SUMMARY errors={len(errors)}")
        return 1 if errors else 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FRONTIER_FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
