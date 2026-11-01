#!/usr/bin/env python3
"""Source-pinned literal edits, including an actually empty fenced replacement.

V1 remains reproducible. This reader consumes every byte of the recipe in order;
it never searches past a malformed block. The same unique, nonoverlapping source
anchors and ID/hash checks apply to deletions as to nonempty replacements.
"""
from __future__ import annotations

from scripts import p106b_hold_resolution_text_edits as previous

FENCE = previous.FENCE
sha = previous.sha
require = previous.require


def parse_recipe(text, *, source_id, base, base_sha256):
    # Keep the exact V1 header contract; no free prose or inferred commands.
    first = text.find("## Change ")
    require(first >= 0, "recipe has no actual text replacements")
    header = text[:first]
    require(header.startswith("# P106B_LITERAL_TEXT_EDITS_V1" + chr(10)), "unsupported recipe schema")
    headers = {}
    for line in header.splitlines()[1:]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        require(separator and key in {"source_id", "base", "base_sha256", "reason"} and key not in headers,
                "invalid or repeated recipe header")
        headers[key] = value.strip()
    require(headers.get("source_id") == source_id, "recipe source ID differs")
    require(headers.get("base") == base and base in {"original", "candidate"}, "recipe base differs")
    require(headers.get("base_sha256") == base_sha256 and previous.re.fullmatch(r"[A-F0-9]{64}", base_sha256),
            "recipe source/candidate hash differs")
    require(bool(headers.get("reason")), "recipe lacks a textual reason")
    cursor = first
    changes = []
    newline = chr(10)
    closing = newline + FENCE
    while text[cursor:].strip():
        # Only blank separator lines are allowed between consecutive blocks.
        while cursor < len(text) and text[cursor] in " \t\r\n":
            cursor += 1
        prefix = "## Change " + str(len(changes) + 1) + newline + "ORIGINAL" + newline + FENCE + "text" + newline
        require(text.startswith(prefix, cursor), "unparsed text or nonconsecutive recipe change")
        cursor += len(prefix)
        stop = text.find(closing, cursor)
        require(stop >= 0, "missing source anchor delimiter")
        before = text[cursor:stop]
        require(before and FENCE not in before, "empty or colliding source anchor")
        cursor = stop + len(closing)
        middle = newline + "REPLACEMENT" + newline + FENCE + "text" + newline
        require(text.startswith(middle, cursor), "missing replacement opening delimiter")
        cursor += len(middle)
        if text.startswith(FENCE, cursor):
            # A Markdown empty fence needs no extra blank content line.
            after = ""
            cursor += len(FENCE)
        else:
            stop = text.find(closing, cursor)
            require(stop >= 0, "missing replacement closing delimiter")
            after = text[cursor:stop]
            require(FENCE not in after, "recipe delimiter collides with literal content")
            cursor = stop + len(closing)
        require(cursor == len(text) or text[cursor] == newline, "extra text after recipe delimiter")
        require(before != after, "ineffective source anchor")
        changes.append((before, after))
    require(changes, "recipe has no actual text replacements")
    return headers, changes


def apply_recipe(original, recipe, *, source_id, base="original"):
    headers, changes = parse_recipe(recipe, source_id=source_id, base=base, base_sha256=sha(original))
    located = []
    for before, after in changes:
        require(original.count(before) == 1, "source text anchor must occur exactly once")
        start = original.index(before)
        located.append((start, start + len(before), before, after))
    located.sort()
    require(all(a[1] <= b[0] for a, b in zip(located, located[1:])), "source anchors overlap")
    text = original
    for lo, hi, before, after in reversed(located):
        text = text[:lo] + after + text[hi:]
    require(text.strip(), "an empty body must be explicitly excluded")
    return text, dict(source_id=source_id, base=base, base_sha256=sha(original), text_sha256=sha(text),
                      reason=headers["reason"], parser="P106B_LITERAL_EMPTY_REPLACEMENT_V2",
                      changes=[dict(original_characters=[lo, hi], original_sha256=sha(before),
                                    replacement_sha256=sha(after)) for lo, hi, before, after in located])
