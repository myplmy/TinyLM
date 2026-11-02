"""Flag partial numeric edits; whole-atom removal remains a semantic review task."""
import difflib
import re

ATOM = re.compile(r"[+\-−]?\d+(?:[.,]\d+)*(?:[eE][+\-−]?\d+)?")


def numeric_atom_changes(original, body):
    if original == body:
        return []
    source_lines = original.splitlines(keepends=True)
    body_lines = body.splitlines(keepends=True)
    source_offsets = [0]
    body_offsets = [0]
    for line in source_lines:
        source_offsets.append(source_offsets[-1] + len(line))
    for line in body_lines:
        body_offsets.append(body_offsets[-1] + len(line))
    correspondence = [None] * len(body)
    matcher = difflib.SequenceMatcher(None, source_lines, body_lines, autojunk=False)
    for tag, a, b, c, d in matcher.get_opcodes():
        if tag == 'equal':
            length = body_offsets[d] - body_offsets[c]
            correspondence[body_offsets[c]:body_offsets[d]] = range(source_offsets[a], source_offsets[a]+length)
        elif tag == 'replace':
            before = original[source_offsets[a]:source_offsets[b]]
            after = body[body_offsets[c]:body_offsets[d]]
            pairs = difflib.SequenceMatcher(None, before, after,
                autojunk=max(len(before), len(after)) > 20000)
            for x, y, size in pairs.get_matching_blocks():
                start = body_offsets[c] + y
                correspondence[start:start+size] = range(source_offsets[a]+x, source_offsets[a]+x+size)
    source_atoms = list(ATOM.finditer(original))
    source_at = {}
    for atom in source_atoms:
        for position in range(atom.start(), atom.end()):
            source_at[position] = atom
    flags = []
    for atom in ATOM.finditer(body):
        mapped = correspondence[atom.start():atom.end()]
        first = mapped[0]
        source_atom = source_at.get(first) if first is not None else None
        exact = (source_atom is not None
            and mapped == list(range(source_atom.start(), source_atom.end()))
            and atom.group() == source_atom.group())
        if exact:
            continue
        flags.append(dict(body_span=[atom.start(), atom.end()], body_token=atom.group(),
            source_token=source_atom.group() if source_atom else None,
            source_span=[source_atom.start(), source_atom.end()] if source_atom else None,
            kind='NUMERIC_ATOM_REQUIRES_EXACT_SOURCE_REVIEW'))
    return flags
