#!/usr/bin/env python3
"""Validate self-declared metadata for every ``ai_dev_tool/**/*.md`` file.

The document inventory is discovered at runtime.  The policy TSV contains only
type rules and the small set of stable pairs; it is deliberately not a file
manifest.  This makes a newly added Markdown file fail for missing metadata
without requiring a second registry edit.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "docs" / "doc_metadata_policy.tsv"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FIELD_RE = re.compile(r"\*\*(?P<key>[^*]+)\*\*\s*:\s*(?P<value>[^·\r\n]+)")

KEY_ALIASES = {
    "최신 갱신일자": "latest_update",
    "Last updated": "latest_update",
    "작성일": "authored",
    "Created": "authored",
    "기준일": "as_of",
    "As of": "as_of",
    "문서 유형": "type",
    "Document type": "type",
    "상태": "status",
    "Status": "status",
}
COUNT_ALIASES = {
    "gate_count": ("gate", "게이트"),
    "human_count": ("human", "사람"),
    "fact_count": ("fact", "사실"),
}


@dataclass(frozen=True)
class TypeRule:
    name: str
    required_date_fields: tuple[str, ...]
    required_fields: tuple[str, ...]
    git_policy: str
    mtime_policy: str


@dataclass(frozen=True)
class PairRule:
    name: str
    left: str
    right: str
    equal_fields: tuple[str, ...]


@dataclass
class Finding:
    path: str
    fields: dict[str, str]
    declared_date: str | None = None


def _split(value: str, separator: str = ",") -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(separator) if part.strip())


def load_policy(path: Path) -> tuple[dict[str, TypeRule], list[PairRule], list[str]]:
    errors: list[str] = []
    types: dict[str, TypeRule] = {}
    pairs: list[PairRule] = []
    pair_names: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        required_columns = {
            "record_type", "name", "required_date_fields", "required_fields",
            "git_policy", "mtime_policy", "left", "right", "equal_fields", "reason",
        }
        if set(rows.fieldnames or ()) != required_columns:
            return {}, [], [f"policy columns mismatch: {rows.fieldnames}"]
        for line_no, row in enumerate(rows, 2):
            record_type = row["record_type"].strip()
            name = row["name"].strip()
            if record_type == "type":
                if name in types:
                    errors.append(f"policy:{line_no}: duplicate type {name}")
                    continue
                types[name] = TypeRule(
                    name=name,
                    required_date_fields=_split(row["required_date_fields"], "|"),
                    required_fields=_split(row["required_fields"]),
                    git_policy=row["git_policy"].strip(),
                    mtime_policy=row["mtime_policy"].strip(),
                )
            elif record_type == "pair":
                if name in pair_names:
                    errors.append(f"policy:{line_no}: duplicate pair {name}")
                    continue
                pair_names.add(name)
                pairs.append(PairRule(
                    name=name,
                    left=row["left"].strip(),
                    right=row["right"].strip(),
                    equal_fields=_split(row["equal_fields"]),
                ))
            else:
                errors.append(f"policy:{line_no}: unknown record_type {record_type!r}")
    if set(types) != {"live", "draft", "snapshot"}:
        errors.append(f"policy types must be live,draft,snapshot; found={sorted(types)}")
    return types, pairs, errors


def parse_metadata(path: Path) -> tuple[dict[str, str], list[str]]:
    text = path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    errors: list[str] = []
    for line in text.splitlines()[:20]:
        for match in FIELD_RE.finditer(line):
            raw_key = match.group("key").strip()
            key = KEY_ALIASES.get(raw_key)
            if key is None:
                continue
            value = match.group("value").strip()
            if key in fields:
                errors.append(f"duplicate metadata field {raw_key}")
            else:
                fields[key] = value

    # Counts are embedded in the existing Rule-counts metadata value, not
    # represented as independent key/value pairs.
    head = "\n".join(text.splitlines()[:20])
    for normalized, labels in COUNT_ALIASES.items():
        matches: list[str] = []
        for label in labels:
            matches.extend(re.findall(rf"`\[{re.escape(label)}\]`\s+(\d+)", head))
        if matches:
            if len(set(matches)) != 1:
                errors.append(f"conflicting {normalized}: {matches}")
            else:
                fields[normalized] = matches[0]
    return fields, errors


def _parse_date(value: str, label: str, errors: list[str]) -> dt.date | None:
    if not DATE_RE.fullmatch(value):
        errors.append(f"{label}: invalid date {value!r}")
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: invalid calendar date {value!r}")
        return None


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )


def git_state(root: Path, relative: str) -> tuple[str | None, bool, str | None]:
    tracked = _git(root, "ls-files", "--error-unmatch", "--", relative)
    if tracked.returncode != 0:
        return None, True, None
    latest = _git(root, "log", "-1", "--format=%cs", "--", relative)
    if latest.returncode != 0:
        return None, False, (latest.stderr or latest.stdout).strip()
    date_text = latest.stdout.strip() or None
    unstaged = _git(root, "diff", "--quiet", "--", relative).returncode != 0
    staged = _git(root, "diff", "--cached", "--quiet", "--", relative).returncode != 0
    return date_text, unstaged or staged, None


def discover(root: Path, scope: str) -> list[Path]:
    base = root / "ai_dev_tool"
    files = sorted(path for path in base.rglob("*.md") if path.is_file())
    if scope == "codex":
        codex = base / "Codex"
        files = [path for path in files if codex in path.parents]
    return files


def validate(
    root: Path,
    policy_path: Path,
    *,
    scope: str = "all",
    today: dt.date | None = None,
    as_of: dt.date | None = None,
    mtime_mode: str = "off",
) -> tuple[list[str], list[str], list[Finding]]:
    today = today or dt.date.today()
    type_rules, pair_rules, errors = load_policy(policy_path)
    warnings: list[str] = []
    findings: list[Finding] = []
    by_relative: dict[str, Finding] = {}

    files = discover(root, scope)
    if not files:
        errors.append(f"no Markdown files discovered for scope={scope}")
        return errors, warnings, findings

    for path in files:
        relative = path.relative_to(root).as_posix()
        fields, parse_errors = parse_metadata(path)
        errors.extend(f"{relative}: {problem}" for problem in parse_errors)
        finding = Finding(path=relative, fields=fields)
        findings.append(finding)
        by_relative[relative] = finding

        document_type = fields.get("type")
        if document_type is None:
            errors.append(f"{relative}: missing document type")
            continue
        rule = type_rules.get(document_type)
        if rule is None:
            errors.append(f"{relative}: unknown document type {document_type!r}")
            continue
        for required in rule.required_fields:
            if not fields.get(required):
                errors.append(f"{relative}: missing required field {required}")

        present_dates = [name for name in rule.required_date_fields if fields.get(name)]
        if len(present_dates) != 1:
            errors.append(
                f"{relative}: expected exactly one of date fields "
                f"{rule.required_date_fields}, found={present_dates}"
            )
            continue
        date_name = present_dates[0]
        declared_text = fields[date_name]
        finding.declared_date = declared_text
        declared = _parse_date(declared_text, relative, errors)
        if declared is None:
            continue
        if declared > today:
            errors.append(f"{relative}: future declared date {declared_text} > {today}")

        if rule.git_policy == "git_not_older_than":
            git_date_text, dirty, git_error = git_state(root, relative)
            if git_error:
                errors.append(f"{relative}: git query failed: {git_error}")
            elif git_date_text:
                git_date = _parse_date(git_date_text, f"{relative} git", errors)
                if git_date is not None and declared < git_date:
                    errors.append(
                        f"{relative}: declared {declared} older than Git content date {git_date}"
                    )
            if dirty and as_of is not None and declared < as_of:
                errors.append(
                    f"{relative}: dirty live document declares {declared} before --as-of {as_of}"
                )
        elif rule.git_policy != "none":
            errors.append(f"policy type {rule.name}: unknown git_policy {rule.git_policy!r}")

        if mtime_mode != "off" and rule.mtime_policy == "optional":
            mtime_date = dt.datetime.fromtimestamp(path.stat().st_mtime).date()
            if mtime_date != declared:
                message = f"{relative}: declared {declared} differs from local mtime {mtime_date}"
                if mtime_mode == "strict":
                    errors.append(message)
                else:
                    warnings.append(message)
        elif rule.mtime_policy not in {"optional", "ignore"}:
            errors.append(f"policy type {rule.name}: unknown mtime_policy {rule.mtime_policy!r}")

    for pair in pair_rules:
        # A scoped Codex run intentionally does not read the root legacy pair.
        selected = [side in by_relative for side in (pair.left, pair.right)]
        if scope != "all" and selected == [False, False]:
            continue
        if selected != [True, True]:
            errors.append(f"policy pair {pair.name}: missing endpoint left={selected[0]} right={selected[1]}")
            continue
        left = by_relative[pair.left]
        right = by_relative[pair.right]
        for field in pair.equal_fields:
            left_value = left.declared_date if field == "date" else left.fields.get(field)
            right_value = right.declared_date if field == "date" else right.fields.get(field)
            if left_value is None or right_value is None:
                errors.append(f"policy pair {pair.name}: missing comparable field {field}")
            elif left_value != right_value:
                errors.append(
                    f"policy pair {pair.name}: {field} differs "
                    f"left={left_value!r} right={right_value!r}"
                )

    return errors, warnings, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ai_dev_tool Markdown metadata validator")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--scope", choices=("all", "codex"), default="all")
    parser.add_argument("--today", type=dt.date.fromisoformat)
    parser.add_argument("--as-of", type=dt.date.fromisoformat)
    mtime = parser.add_mutually_exclusive_group()
    mtime.add_argument("--local-mtime-warn", action="store_true")
    mtime.add_argument("--local-mtime-strict", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    policy = args.policy if args.policy.is_absolute() else root / args.policy
    mode = "strict" if args.local_mtime_strict else "warn" if args.local_mtime_warn else "off"
    errors, warnings, findings = validate(
        root,
        policy.resolve(),
        scope=args.scope,
        today=args.today,
        as_of=args.as_of,
        mtime_mode=mode,
    )
    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[FAIL] {error}")
    counts: dict[str, int] = {}
    for finding in findings:
        doc_type = finding.fields.get("type", "missing")
        counts[doc_type] = counts.get(doc_type, 0) + 1
    count_text = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    if errors:
        print(f"[FAIL] documents={len(findings)}; errors={len(errors)}; warnings={len(warnings)}; {count_text}")
        return 1
    print(f"[PASS] documents={len(findings)}; errors=0; warnings={len(warnings)}; {count_text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
