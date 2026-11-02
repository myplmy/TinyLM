"""Prove flagged atoms are exact ordered values in the same changed block."""
import difflib
import re
from numeric_atom_integrity_v1 import ATOM

UNIT = re.compile(r'[ \t]*(년|개월|월|일|세기|세손|세|살|명|개|권|편|배|회|km|cm|mm|kg|m|s|도|°|%|K|C)')


def atoms(text, offset):
    result = []
    for match in ATOM.finditer(text):
        unit = UNIT.match(text, match.end())
        result.append(dict(value=match.group(), unit=unit[1] if unit else '',
            span=[offset + match.start(), offset + match.end()]))
    return result


def prove_flagged_atoms(original, body, flags):
    source_lines, body_lines = original.splitlines(keepends=True), body.splitlines(keepends=True)
    source_offsets, body_offsets = [0], [0]
    for line in source_lines:
        source_offsets.append(source_offsets[-1] + len(line))
    for line in body_lines:
        body_offsets.append(body_offsets[-1] + len(line))
    mappings = {}
    for tag, a, b, c, d in difflib.SequenceMatcher(None, source_lines, body_lines, autojunk=False).get_opcodes():
        if tag == 'delete':
            continue
        before = atoms(original[source_offsets[a]:source_offsets[b]], source_offsets[a])
        after = atoms(body[body_offsets[c]:body_offsets[d]], body_offsets[c])
        cursor, mapping = 0, {}
        for target in after:
            while cursor < len(before) and (before[cursor]['value'], before[cursor]['unit']) != (target['value'], target['unit']):
                cursor += 1
            if cursor == len(before):
                mapping = {}
                break
            mapping[tuple(target['span'])] = dict(original_atom=before[cursor], body_atom=target,
                original_changed_lines=[a + 1, b], body_changed_lines=[c + 1, d])
            cursor += 1
        mappings.update(mapping)
    results = []
    for flag in flags:
        match = mappings.get(tuple(flag['body_span']))
        results.append(dict(flag=flag, status='EXACT_LOCAL_ATOM_AND_UNIT' if match else 'MANUAL_CONTEXT_REQUIRED',
            proof=match, semantic_or_fact_approval=False))
    return results
