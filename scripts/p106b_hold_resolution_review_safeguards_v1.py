#!/usr/bin/env python3
"""Fail closed on unparsed explicit decisions and partial reading-view bodies."""
import re

DECISION = re.compile(r"\b(?:ACCEPT_CANDIDATE|ADOPT_CANDIDATE|REVISE_TEXT|EDIT_TEXT|EDIT_RECIPE|KEEP_SOURCE|EXCLUDE|NEEDS_ROOT|HOLD)\b")
EXPLICIT_ID = re.compile(r"(?:expanded_train|historical_train|validation)[:_]\d+")


def canonical_id(value):
    return value.replace("_train_", "_train:").replace("validation_", "validation:")


def unparsed_declared_review_ids(payload, parsed_ids, expected):
    """A declaration is only a missing-evidence signal, never an approval.

    Only explicit heading/ID labels or a decision table row can name a source.
    Incidental prose mentions and files with no declared decision are ignored.
    """
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    if not DECISION.search(text):
        return set()
    declared = set()
    for line in text.splitlines():
        label = bool(re.match(r"^#{1,6}[ \t]+", line) or re.match(r"^[ \t]*[-*]?[ \t]*\*{0,2}ID\b", line, re.I))
        table = line.startswith("|") and DECISION.search(line)
        if not label and not table:
            continue
        declared.update(canonical_id(value) for value in EXPLICIT_ID.findall(line))
        if label:
            bare = re.search(r"\bID[ \t:：]+([0-9]+)\b", line, re.I)
            if bare:
                declared.add("expanded_train:" + bare[1])
    return (declared & set(expected)) - set(parsed_ids)


def partial_reading_view_collisions(source_id, body_sha256, manifest):
    """Return only exact hashes of a proper subwindow of its assigned input.

    This diagnostic uses source-linked window metadata, with no arbitrary
    length-loss threshold and no inference that a short valid body is bad.
    An exact root exception, if needed, must be handled outside this helper.
    """
    matches = []
    for row in manifest["rows"]:
        if row["id"] != source_id:
            continue
        for kind, views in row["views"].items():
            if kind not in {"original", "candidate"} or len(views) < 2:
                continue
            total = views[-1]["source_characters"][1]
            for view in views:
                lo, hi = view["source_characters"]
                if view["sha256"] == body_sha256 and (lo > 0 or hi < total):
                    matches.append(dict(kind=kind, view=view, full_source_characters=total))
    return matches
