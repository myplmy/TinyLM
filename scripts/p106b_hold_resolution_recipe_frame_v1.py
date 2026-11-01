#!/usr/bin/env python3
"""Compile unambiguous recipe framing; never repair source anchors or text.

Only source-pinned header spelling, an explicit opening fence's language label
and increasing change numbers may normalize. The frozen strict v2 applier still
checks every literal anchor exactly once and rejects overlapping source spans.
"""
from __future__ import annotations

import re
from pathlib import Path
from scripts import p106b_hold_resolution_text_edits_v2 as strict

FENCE = strict.FENCE
require = strict.require


def canonicalize(recipe, *, source_id, paths, root):
    require(chr(13) not in recipe, "recipe frame compiler requires literal LF input")
    lines = recipe.split(chr(10))
    require(lines[0] in {"# P106B_LITERAL_TEXT_EDITS_V1", "# Strict literal edit recipe"}, "unknown author recipe schema")
    header, index = {}, 1
    while index < len(lines) and not lines[index].startswith("## Change "):
        line = lines[index]
        index += 1
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        require(sep and key in {"source_id", "base", "base_sha256", "reason"} and key not in header, "invalid author recipe metadata")
        header[key] = value.strip()
    require(header.get("source_id") in {source_id, source_id.replace(":", "_")}, "author source ID differs")
    require(header.get("reason"), "author reason missing")
    declared = header.get("base")
    matches = []
    for label in ["original", "candidate"]:
        info = paths[label]
        alternatives = {label, info["path"], str(root / info["path"])}
        if declared in alternatives and header.get("base_sha256") == info["sha256"]:
            matches.append(label)
    require(matches, "author base path/hash is not a pinned TASK input")
    # An identical original/candidate physical path is an explicit byte alias.
    require(len(matches) == 1 or paths["original"] == paths["candidate"], "ambiguous author base")
    base = matches[0]
    changes, previous_number = [], 0

    def read_block(cursor):
        require(cursor < len(lines) and lines[cursor] in {FENCE, FENCE + "text"}, "explicit eight-backtick opening fence missing")
        cursor += 1
        start = cursor
        while cursor < len(lines) and lines[cursor] != FENCE:
            require(not lines[cursor].startswith("## Change "), "unterminated literal block before next change")
            cursor += 1
        require(cursor < len(lines), "literal closing fence missing")
        return chr(10).join(lines[start:cursor]), cursor + 1

    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        match = re.fullmatch(r"## Change ([0-9]+)", lines[index])
        require(match and int(match[1]) > previous_number, "changes must have unique increasing numbers")
        number = int(match[1])
        previous_number = number
        index += 1
        require(index < len(lines) and lines[index] == "ORIGINAL", "literal ORIGINAL marker missing")
        before, index = read_block(index + 1)
        require(index < len(lines) and lines[index] == "REPLACEMENT", "literal REPLACEMENT marker missing")
        after, index = read_block(index + 1)
        require(before, "empty source anchor")
        changes.append((number, before, after))
    require(changes, "no actual authored text edits")
    output = ["# P106B_LITERAL_TEXT_EDITS_V1", "source_id: " + source_id, "base: " + base,
              "base_sha256: " + paths[base]["sha256"], "reason: " + header["reason"], ""]
    for ordinal, (_, before, after) in enumerate(changes, 1):
        output += ["## Change " + str(ordinal), "ORIGINAL", FENCE + "text", before, FENCE,
                   "REPLACEMENT", FENCE + "text", after, FENCE, ""]
    canonical = chr(10).join(output)
    # Parse the generated frame again; anchor/replacement strings cannot change.
    _, parsed = strict.parse_recipe(canonical, source_id=source_id, base=base, base_sha256=paths[base]["sha256"])
    require(parsed == [(before, after) for _, before, after in changes], "frame compiler changed an authored literal")
    return canonical, dict(base=base, original_recipe_sha256=strict.sha(recipe), canonical_recipe_sha256=strict.sha(canonical),
                           changed=recipe != canonical, authored_change_numbers=[number for number, _, _ in changes],
                           literal_strings_unchanged=True, root_approved=False)
