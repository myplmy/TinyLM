#!/usr/bin/env python3
"""Create a TinyLM proposal from the canonical template.

Default routing comes from .agents/project.json.  A user-named exceptional path
must be supplied literally with --exact-path and recorded with --authority; the
exception applies to this artifact only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / ".agents" / "project.json"
PROTECTED = "datasets/TinyDataset/"


def route() -> dict[str, object]:
    data = json.loads(PROJECT.read_text(encoding="utf-8"))
    return data["documentRouting"]["proposal"]


def safe_relative(raw: str) -> Path:
    candidate = Path(raw.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must be repository-relative without '..'")
    normal = candidate.as_posix()
    if normal == PROTECTED.rstrip("/") or normal.startswith(PROTECTED):
        raise ValueError("protected dataset path is never a proposal target")
    if candidate.suffix.lower() != ".md":
        raise ValueError("proposal target must end in .md")
    return candidate


def render(template: str, *, title: str, date: str, category: str, destination: Path) -> str:
    text = template.replace("{한 줄 제목}", title)
    text = text.replace("{YYYY-MM-DD}", date)
    text = text.replace("{실험계획 / 아키텍처 / 스킬 / 작업방식}", category)
    readme = os.path.relpath(ROOT / "proposal" / "README.md", (ROOT / destination).parent)
    readme = readme.replace("\\", "/")
    return text.replace("[`proposal/README.md`](README.md)", f"[`proposal/README.md`]({readme})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--slug", required=True, help="ASCII/Korean filename slug without extension")
    parser.add_argument("--category", required=True, choices=("실험계획", "아키텍처", "스킬", "작업방식"))
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--exact-path", help="literal user-requested repository-relative output path")
    parser.add_argument("--authority", help="exact user instruction authorizing --exact-path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        print("FAIL --date must be YYYY-MM-DD")
        return 2
    config = route()
    default_dir = Path(str(config["defaultDir"]))
    if args.exact_path:
        if not args.authority or not args.authority.strip():
            print("FAIL --exact-path requires non-empty --authority")
            return 2
        try:
            relative = safe_relative(args.exact_path)
        except ValueError as exc:
            print(f"FAIL {exc}")
            return 2
    else:
        slug = args.slug.strip().replace(" ", "-")
        if not slug or "/" in slug or "\\" in slug or slug.lower().startswith("temp_"):
            print("FAIL default slug must be one filename and must not start with temp_")
            return 2
        relative = default_dir / f"{args.date.replace('-', '')}_{slug}.md"

    if relative.name.lower().startswith(str(config["temporaryPrefix"]).lower()) and not args.exact_path:
        print("FAIL temp_ is allowed only for an explicitly authorized exact path")
        return 2
    output = ROOT / relative
    if output.exists():
        print(f"FAIL target already exists: {relative.as_posix()}")
        return 2
    template = (ROOT / str(config["template"])).read_text(encoding="utf-8")
    body = render(template, title=args.title, date=args.date, category=args.category, destination=relative)
    print(f"TARGET {relative.as_posix()}")
    print(f"ROUTE {'explicit' if args.exact_path else 'default'}")
    if args.dry_run:
        print("RESULT DRY_RUN")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    with io.open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    os.replace(temporary, output)
    print("RESULT CREATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
