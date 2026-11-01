#!/usr/bin/env python3
"""Normalize an exact TASK-qualified source ID, without changing text anchors.

The TASK namespace and base SHA still have to match the caller's exact source.
All literal blocks and the frozen strict applier retain their original checks.
"""
import re
from scripts import p106b_hold_resolution_recipe_frame_v1 as previous

strict, FENCE, require = previous.strict, previous.FENCE, previous.require


def canonicalize(recipe, *, source_id, paths, root):
    lines = recipe.split(chr(10))
    changed = False
    metadata_end = next((i for i, line in enumerate(lines) if line.startswith('## Change ')), len(lines))
    indexes = [i for i in range(metadata_end) if lines[i].startswith('source_id:')]
    if len(indexes) == 1:
        index = indexes[0]
        declared = lines[index].partition(':')[2].strip()
        qualified = re.fullmatch(r'TASK_[0-9]+(?:[ \t]+(?:original|candidate))?:[ \t]*' + re.escape(source_id), declared)
        if qualified:
            lines[index] = 'source_id: ' + source_id
            changed = True
    normalized = chr(10).join(lines)
    canonical, proof = previous.canonicalize(normalized, source_id=source_id, paths=paths, root=root)
    # No declaration with another ID, ambiguous base, wrong hash, changed
    # literal or overlapping source spans is repaired by this wrapper.
    proof = dict(proof, original_recipe_sha256=strict.sha(recipe),
                 source_task_prefix_normalized=changed, changed=canonical != recipe,
                 frame_compiler='TASK_QUALIFIED_SOURCE_ID_V2')
    return canonical, proof
