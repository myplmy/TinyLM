#!/usr/bin/env python3
"""TinyLM result condition-signature validator (CPU/static only).

The checker never discovers result files on its own.  Every document must be
passed explicitly so callers can keep protected paths out of scope.

Block format::

    <!-- TINYLM_CONDITION_SIGNATURE_V1 id=example -->
    | field | arm_a | arm_b | evidence |
    | --- | --- | --- | --- |
    | pool_id | ... | ... | ... |
    ...
    <!-- /TINYLM_CONDITION_SIGNATURE_V1 -->

The schema records observed conditions; it does not infer missing values from
file names or silently promote UNKNOWN values to matched controls.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


START_RE = re.compile(
    r"<!--\s*TINYLM_CONDITION_SIGNATURE_V1\s+id=([A-Za-z0-9_.:-]+)\s*-->"
)
END = "<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->"
CLAIMS = {"DIRECT_PAIRED", "PARTIAL_CONFOUNDED", "DESCRIPTIVE_ONLY", "NOT_RUN"}

REQUIRED_FIELDS = (
    "pool_id",
    "actual_pool_tokens",
    "pool_override",
    "steps",
    "micro_bs",
    "accum",
    "seq",
    "actual_draw_tokens",
    "sampler_with_replacement",
    "expected_unique_tokens",
    "sequential_epoch_claim",
    "scheduler",
    "warmup",
    "anneal_start",
    "decay_fraction",
    "absolute_schedule_horizon",
    "train_language_expected",
    "train_language_observed",
    "eval_dataset",
    "eval_language",
    "tokenizer",
    "grad_ckpt",
    "comparator_tag",
    "matched_axes",
    "changed_axes",
    "unmeasured_axes",
    "not_run_claims",
    "permitted_claim",
)
META_FIELDS = {
    "comparator_tag",
    "matched_axes",
    "changed_axes",
    "unmeasured_axes",
    "not_run_claims",
    "permitted_claim",
}
DIRECT_CONTROL_AXES = {
    "pool_id",
    "actual_pool_tokens",
    "pool_override",
    "steps",
    "micro_bs",
    "accum",
    "seq",
    "actual_draw_tokens",
    "sampler_with_replacement",
    "scheduler",
    "warmup",
    "anneal_start",
    "decay_fraction",
    "absolute_schedule_horizon",
    "train_language_expected",
    "train_language_observed",
    "eval_dataset",
    "eval_language",
    "tokenizer",
    "grad_ckpt",
}
UNKNOWN_MARKERS = ("UNKNOWN", "NOT_MEASURED", "미계측", "미상")


@dataclass(frozen=True)
class Row:
    arm_a: str
    arm_b: str
    evidence: str


@dataclass(frozen=True)
class Signature:
    ident: str
    rows: dict[str, Row]
    line: int


def _cells(line: str) -> list[str]:
    if not line.strip().startswith("|"):
        return []
    return [part.strip() for part in line.strip().strip("|").split("|")]


def parse_signatures(text: str) -> tuple[list[Signature], list[str]]:
    lines = text.splitlines()
    signatures: list[Signature] = []
    errors: list[str] = []
    i = 0
    seen_ids: set[str] = set()
    while i < len(lines):
        match = START_RE.fullmatch(lines[i].strip())
        if not match:
            i += 1
            continue
        ident = match.group(1)
        start_line = i + 1
        if ident in seen_ids:
            errors.append(f"line {start_line}: duplicate signature id {ident!r}")
        seen_ids.add(ident)
        i += 1
        body: list[tuple[int, str]] = []
        while i < len(lines) and lines[i].strip() != END:
            body.append((i + 1, lines[i]))
            i += 1
        if i >= len(lines):
            errors.append(f"line {start_line}: signature {ident!r} has no closing marker")
            break
        i += 1
        table = [(n, _cells(line)) for n, line in body if line.strip().startswith("|")]
        if len(table) < 2 or table[0][1] != ["field", "arm_a", "arm_b", "evidence"]:
            errors.append(
                f"line {start_line}: signature {ident!r} needs exact table header "
                "'| field | arm_a | arm_b | evidence |'"
            )
            continue
        rows: dict[str, Row] = {}
        for line_no, cells in table[2:]:
            if len(cells) != 4:
                errors.append(f"line {line_no}: expected four table cells")
                continue
            field, arm_a, arm_b, evidence = cells
            if field in rows:
                errors.append(f"line {line_no}: duplicate field {field!r}")
                continue
            if not field or not arm_a or not arm_b or not evidence:
                errors.append(f"line {line_no}: empty condition-signature cell")
                continue
            rows[field] = Row(arm_a, arm_b, evidence)
        signatures.append(Signature(ident, rows, start_line))
    return signatures, errors


def _csv(value: str) -> set[str]:
    if value in {"-", "—", "NONE"}:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _integer(value: str) -> int | None:
    compact = value.replace(",", "").replace("_", "").strip()
    return int(compact) if re.fullmatch(r"\d+", compact) else None


def validate_signature(sig: Signature) -> list[str]:
    errors: list[str] = []
    missing = [field for field in REQUIRED_FIELDS if field not in sig.rows]
    if missing:
        errors.append(f"{sig.ident}: missing fields: {', '.join(missing)}")
        return errors

    claim = sig.rows["permitted_claim"].arm_a
    if claim not in CLAIMS:
        errors.append(f"{sig.ident}: invalid permitted_claim {claim!r}")

    axes = set(sig.rows) - META_FIELDS
    matched = _csv(sig.rows["matched_axes"].arm_a)
    changed = _csv(sig.rows["changed_axes"].arm_a)
    unmeasured = _csv(sig.rows["unmeasured_axes"].arm_a)
    overlap = (matched & changed) | (matched & unmeasured) | (changed & unmeasured)
    if overlap:
        errors.append(f"{sig.ident}: axes classified more than once: {', '.join(sorted(overlap))}")
    classified = matched | changed | unmeasured
    if axes != classified:
        absent = axes - classified
        unknown = classified - axes
        if absent:
            errors.append(f"{sig.ident}: unclassified axes: {', '.join(sorted(absent))}")
        if unknown:
            errors.append(f"{sig.ident}: classification names unknown axes: {', '.join(sorted(unknown))}")

    for axis in sorted(axes):
        row = sig.rows[axis]
        if row.arm_a == row.arm_b and axis in changed:
            errors.append(f"{sig.ident}: {axis} is equal but classified changed")
        if row.arm_a != row.arm_b and axis in matched:
            errors.append(f"{sig.ident}: {axis} differs but classified matched")

    for arm_name in ("arm_a", "arm_b"):
        values = {field: getattr(sig.rows[field], arm_name) for field in sig.rows}
        nums = {key: _integer(values[key]) for key in ("steps", "micro_bs", "accum", "seq", "actual_draw_tokens")}
        if all(number is not None for number in nums.values()):
            expected = nums["steps"] * nums["micro_bs"] * nums["accum"] * nums["seq"]
            if nums["actual_draw_tokens"] != expected:
                errors.append(
                    f"{sig.ident}: {arm_name} actual_draw_tokens={nums['actual_draw_tokens']} "
                    f"but steps*micro_bs*accum*seq={expected}"
                )

    sched = sig.rows["scheduler"]
    steps = sig.rows["steps"]
    if "wsd" in sched.arm_a.lower() and "wsd" in sched.arm_b.lower() and steps.arm_a != steps.arm_b:
        if "absolute_schedule_horizon" not in changed:
            errors.append(f"{sig.ident}: different WSD steps must classify absolute_schedule_horizon as changed")
        if claim == "DIRECT_PAIRED":
            errors.append(f"{sig.ident}: different WSD horizons cannot be DIRECT_PAIRED")

    if claim == "DIRECT_PAIRED":
        non_controls = (changed | unmeasured) & DIRECT_CONTROL_AXES
        if non_controls:
            errors.append(
                f"{sig.ident}: DIRECT_PAIRED has non-matched control axes: "
                f"{', '.join(sorted(non_controls))}"
            )
        for axis in DIRECT_CONTROL_AXES & axes:
            if axis in unmeasured:
                continue
            row = sig.rows[axis]
            joined = f"{row.arm_a} {row.arm_b}".upper()
            if any(marker.upper() in joined for marker in UNKNOWN_MARKERS):
                errors.append(f"{sig.ident}: DIRECT_PAIRED control {axis} is unresolved")

    eval_lang = f"{sig.rows['eval_language'].arm_a} {sig.rows['eval_language'].arm_b}".lower()
    if ("ko=0%" in eval_lang or "한국어=0%" in eval_lang or "한국어 0%" in eval_lang):
        not_run = _csv(sig.rows["not_run_claims"].arm_a)
        if "KOREAN_QUALITY" not in not_run:
            errors.append(f"{sig.ident}: ko=0% evaluation requires KOREAN_QUALITY in not_run_claims")

    return errors


def check_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{path}: cannot read UTF-8 document: {exc}"]
    signatures, errors = parse_signatures(text)
    if not signatures:
        errors.append(f"{path}: no TINYLM_CONDITION_SIGNATURE_V1 block")
    for sig in signatures:
        errors.extend(f"{path}:{sig.line}: {message}" for message in validate_signature(sig))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="explicit result Markdown files")
    args = parser.parse_args(argv)
    errors: list[str] = []
    count = 0
    for path in args.files:
        signatures, parse_errors = parse_signatures(path.read_text(encoding="utf-8")) if path.is_file() else ([], [f"missing file: {path}"])
        count += len(signatures)
        errors.extend(f"{path}: {message}" for message in parse_errors)
        if path.is_file():
            if not signatures:
                errors.append(f"{path}: no TINYLM_CONDITION_SIGNATURE_V1 block")
            for sig in signatures:
                errors.extend(f"{path}:{sig.line}: {message}" for message in validate_signature(sig))
    for error in errors:
        print(f"FAIL {error}")
    if errors:
        print(f"RESULT FAIL files={len(args.files)} signatures={count} errors={len(errors)}")
        return 1
    print(f"RESULT PASS files={len(args.files)} signatures={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
