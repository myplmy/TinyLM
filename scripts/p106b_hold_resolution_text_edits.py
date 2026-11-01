#!/usr/bin/env python3
"""Apply source-pinned text replacements authored as Markdown data.

This never executes a recipe. Anchors refer to the same original base, must be
unique and nonoverlapping, and cannot be applied to another source/candidate.
Semantic approval and code/Unicode guards remain separate admission gates.
"""
from __future__ import annotations

import hashlib
import re

FENCE = "````````"
BLOCK = re.compile(r"(?ms)^## Change ([1-9][0-9]*)\nORIGINAL\n" + FENCE + r"text\n(.*?)\n" + FENCE
                   + r"\nREPLACEMENT\n" + FENCE + r"text\n(.*?)\n" + FENCE + r"(?:\n|$)")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def parse_recipe(text, *, source_id, base, base_sha256):
    require(text.startswith("# P106B_LITERAL_TEXT_EDITS_V1" + chr(10)), "unsupported recipe schema")
    headers = {}
    first = text.find("## Change ")
    require(first >= 0, "recipe has no actual text replacements")
    for line in text[:first].splitlines()[1:]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        require(separator and key in {"source_id", "base", "base_sha256", "reason"} and key not in headers, "invalid or repeated recipe header")
        headers[key] = value.strip()
    require(headers.get("source_id") == source_id, "recipe source ID differs")
    require(headers.get("base") == base and base in {"original", "candidate"}, "recipe base differs")
    require(headers.get("base_sha256") == base_sha256 and re.fullmatch(r"[A-F0-9]{64}", base_sha256), "recipe source/candidate hash differs")
    require(bool(headers.get("reason")), "recipe lacks a textual reason")
    blocks = []
    end = first
    for match in BLOCK.finditer(text, first):
        require(not text[end:match.start()].strip(), "unparsed text between replacements")
        require(int(match[1]) == len(blocks) + 1, "recipe changes must have consecutive IDs")
        before, after = match[2], match[3]
        require(before and before != after, "empty or ineffective source anchor")
        require(FENCE not in before and FENCE not in after, "recipe delimiter collides with literal content")
        blocks.append((before, after))
        end = match.end()
    require(blocks and not text[end:].strip(), "unparsed or missing recipe replacement")
    return headers, blocks


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
    proof = dict(source_id=source_id, base=base, base_sha256=sha(original), text_sha256=sha(text),
                 reason=headers["reason"], changes=[dict(original_characters=[lo, hi], original_sha256=sha(before),
                                                       replacement_sha256=sha(after)) for lo, hi, before, after in located])
    return text, proof
