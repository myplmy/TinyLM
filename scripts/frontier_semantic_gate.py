#!/usr/bin/env python3
"""C3 manual semantic triage for unfinished plans and approved ongoing proposals."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from frontier_audit import sha256
from frontier_queue_gate import _frontier, _json_hash, scoped_handoff
from handoff_queue import _section

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "TINYLM_FRONTIER_SEMANTIC_V1"
PLAN_VALUES = {"HIGH", "MEDIUM", "LOW", "UNCERTAIN"}
PLAN_DECISIONS = {
    "BUILD_NEXT", "USER_DECISION", "FAILED_GATE", "LOW_PRIORITY",
    "EVIDENCE_NEEDED", "DOC_CORRECTION",
}
PROPOSAL_DECISIONS = {
    "IMPLEMENT_NEXT", "USER_DECISION", "FAILED_GATE", "E2E_PENDING",
    "LOW_PRIORITY", "DOC_REFRESH",
}
MARKER = re.compile(
    r"<!-- TINYLM_FRONTIER_SEMANTIC_V1 "
    r"artifact=(audit/FRONTIER_SEMANTIC_[0-9A-F]{12}_[0-9A-F]{12}\.json) "
    r"sha256=([0-9A-F]{64}) -->"
)


def snapshot(root: Path) -> dict:
    frontier = _frontier(root)
    proposals = sorted((root / "proposal").glob("*-approved-on-going.md"))
    proposal_manifest = [
        {"path": path.relative_to(root).as_posix(), "sha256": sha256(path)}
        for path in proposals
    ]
    source_sha = _json_hash({
        "frontier_source_manifest": frontier["source_manifest"],
        "proposal_manifest": proposal_manifest,
    })
    return {"frontier": frontier, "proposal_manifest": proposal_manifest,
            "source_sha256": source_sha}


def artifact_name(state: dict) -> str:
    return (f"FRONTIER_SEMANTIC_{state['frontier']['frontier_sha256'][:12]}_"
            f"{state['source_sha256'][:12]}.json")


def artifact_path(root: Path, raw: str | Path) -> Path:
    path = Path(raw)
    target = (root / path).resolve() if not path.is_absolute() else path.resolve()
    audit = (root / "handoff" / "audit").resolve()
    if path.is_symlink() or not target.is_relative_to(audit):
        raise ValueError("semantic artifact must be a non-symlink under handoff/audit")
    return target


def prepare(root: Path) -> tuple[Path, dict, bool]:
    state = snapshot(root)
    target = root / "handoff" / "audit" / artifact_name(state)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise ValueError("semantic artifact path is not a regular file")
        return target, state, False
    frontier = state["frontier"]
    document = {
        "schema": SCHEMA,
        "frontier_sha256": frontier["frontier_sha256"],
        "source_sha256": state["source_sha256"],
        "frontier_source_manifest": frontier["source_manifest"],
        "proposal_manifest": state["proposal_manifest"],
        "none_buildable_approval_ref": "",
        "plan_reviews": [
            {"plan_id": row["plan_id"], "plan_path": row["plan_path"],
             "value_tier": "REVIEW_REQUIRED", "decision": "REVIEW_REQUIRED",
             "priority": None, "review": "MANUAL_REQUIRED",
             "reason": "", "evidence": "", "next_action": ""}
            for row in frontier["rows"] if row["disposition_required"]
        ],
        "proposal_reviews": [
            {"path": entry["path"], "decision": "REVIEW_REQUIRED",
             "review": "MANUAL_REQUIRED", "reason": "", "evidence": "",
             "next_action": "", "linked_plans": []}
            for entry in state["proposal_manifest"]
        ],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    return target, state, True


def marker(target: Path, state: dict) -> str:
    return (f"<!-- TINYLM_FRONTIER_SEMANTIC_V1 artifact=audit/{target.name} "
            f"sha256={state['source_sha256']} -->")


def _substantive(value: object, minimum: int = 8) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def verify_artifact(root: Path, raw: str | Path) -> list[str]:
    errors: list[str] = []
    try:
        state = snapshot(root)
        target = artifact_path(root, raw)
        if target.name != artifact_name(state):
            errors.append("semantic artifact name is stale for current sources")
        if not target.is_file():
            return errors + ["semantic artifact absent"]
        data = json.loads(target.read_text(encoding="utf-8"))
        frontier = state["frontier"]
        expected = {
            "schema": SCHEMA,
            "frontier_sha256": frontier["frontier_sha256"],
            "source_sha256": state["source_sha256"],
            "frontier_source_manifest": frontier["source_manifest"],
            "proposal_manifest": state["proposal_manifest"],
        }
        for key, value in expected.items():
            if data.get(key) != value:
                errors.append(f"semantic {key} is stale or invalid")
        current = {row["plan_id"]: row for row in frontier["rows"]
                   if row["disposition_required"]}
        plans = data.get("plan_reviews")
        if not isinstance(plans, list) or any(not isinstance(row, dict) for row in plans):
            return errors + ["semantic plan_reviews missing or invalid"]
        ids = [row.get("plan_id") for row in plans]
        if len(ids) != len(set(ids)) or set(ids) != set(current):
            errors.append("semantic plan IDs missing, duplicated or extra")
        ranks: list[int] = []
        reasons: set[str] = set()
        for row in plans:
            ident = row.get("plan_id")
            if ident not in current:
                continue
            if row.get("plan_path") != current[ident]["plan_path"]:
                errors.append(f"{ident}: plan path mismatch")
            decision = row.get("decision")
            if row.get("review") != "MANUAL" or decision not in PLAN_DECISIONS:
                errors.append(f"{ident}: manual decision missing")
            if row.get("value_tier") not in PLAN_VALUES:
                errors.append(f"{ident}: value tier missing")
            if row.get("value_tier") == "UNCERTAIN" and decision != "EVIDENCE_NEEDED":
                errors.append(f"{ident}: uncertain value needs EVIDENCE_NEEDED")
            for key, minimum in (("reason", 16), ("evidence", 8), ("next_action", 8)):
                if not _substantive(row.get(key), minimum):
                    errors.append(f"{ident}: {key} is empty or generic")
            reason = str(row.get("reason") or "").strip().lower()
            if reason in reasons:
                errors.append(f"{ident}: copied value reason")
            reasons.add(reason)
            if current[ident]["plan_path"] not in str(row.get("evidence") or ""):
                errors.append(f"{ident}: evidence must cite its exact plan path")
            if reason in {
                "런처 없음", "런처 0건", "no launcher", "auto_no_launcher"
            }:
                errors.append(f"{ident}: launcher absence is not value triage")
            rank = row.get("priority")
            if decision == "BUILD_NEXT":
                if row.get("value_tier") == "LOW":
                    errors.append(f"{ident}: LOW value cannot be BUILD_NEXT")
                if type(rank) is not int or rank <= 0:
                    errors.append(f"{ident}: BUILD_NEXT needs positive priority")
                else:
                    ranks.append(rank)
            elif rank is not None:
                errors.append(f"{ident}: non-BUILD_NEXT priority must be null")
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            errors.append("BUILD_NEXT priorities must be unique and contiguous from 1")
        if current and not ranks and not _substantive(
            data.get("none_buildable_approval_ref"), 8
        ):
            errors.append("unfinished plans need BUILD_NEXT or explicit no-build approval")

        expected_proposals = {entry["path"] for entry in state["proposal_manifest"]}
        proposals = data.get("proposal_reviews")
        if not isinstance(proposals, list) or any(not isinstance(row, dict) for row in proposals):
            return errors + ["semantic proposal_reviews missing or invalid"]
        paths = [row.get("path") for row in proposals]
        if len(paths) != len(set(paths)) or set(paths) != expected_proposals:
            errors.append("ongoing proposal paths missing, duplicated or extra")
        all_plan_ids = {row["plan_id"] for row in frontier["rows"]}
        for row in proposals:
            path = row.get("path")
            if path not in expected_proposals:
                continue
            if row.get("review") != "MANUAL" or row.get("decision") not in PROPOSAL_DECISIONS:
                errors.append(f"{path}: manual proposal decision missing")
            for key, minimum in (("reason", 16), ("evidence", 8), ("next_action", 8)):
                if not _substantive(row.get(key), minimum):
                    errors.append(f"{path}: {key} is empty or generic")
            if path not in str(row.get("evidence") or ""):
                errors.append(f"{path}: evidence must cite its exact proposal path")
            linked = row.get("linked_plans")
            if not isinstance(linked, list) or any(
                not isinstance(ident, str) or ident not in all_plan_ids
                for ident in linked
            ):
                errors.append(f"{path}: linked_plans invalid")
        return errors
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return errors + [f"semantic gate error: {type(exc).__name__}: {exc}"]


def verify_handoff(root: Path, handoff: Path) -> list[str]:
    try:
        selected = scoped_handoff(root, handoff)
        marks = MARKER.findall(_section(selected.read_text(encoding="utf-8")))
        if len(marks) != 1:
            return ["handoff needs exactly one current semantic triage marker"]
        relative, stated_sha = marks[0]
        state = snapshot(root)
        errors = []
        if stated_sha != state["source_sha256"]:
            errors.append("semantic handoff source SHA is stale")
        errors.extend(verify_artifact(root, root / "handoff" / relative))
        return errors
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        return [f"semantic handoff error: {type(exc).__name__}: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--artifact")
    parser.add_argument("--handoff")
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.artifact or args.handoff:
                parser.error("--prepare takes no artifact or handoff")
            target, state, created = prepare(ROOT)
            print(f"SEMANTIC_PREPARED path={target.relative_to(ROOT)} created={int(created)} "
                  f"plans={sum(r['disposition_required'] for r in state['frontier']['rows'])} "
                  f"proposals={len(state['proposal_manifest'])}")
            print(marker(target, state))
            return 0
        if bool(args.artifact) == bool(args.handoff):
            parser.error("--check requires exactly one of --artifact or --handoff")
        errors = verify_artifact(ROOT, args.artifact) if args.artifact else verify_handoff(
            ROOT, scoped_handoff(ROOT, args.handoff)
        )
        for error in errors:
            print("SEMANTIC_FAIL " + error)
        print(f"SEMANTIC_SUMMARY errors={len(errors)}")
        return 1 if errors else 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"SEMANTIC_FAIL {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
