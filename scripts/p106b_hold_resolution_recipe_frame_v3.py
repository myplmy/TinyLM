#!/usr/bin/env python3
"""Resolve an observed TASK shorthand only against an exact pinned source ID.

This normalizes declared metadata, never a missing/wrong base hash or literal
text. Numeric shorthand is permitted only with a TASK marker and exact ID tail.
"""
import re
from scripts import p106b_hold_resolution_recipe_frame_v2 as previous

strict, FENCE, require = previous.strict, previous.FENCE, previous.require


def canonicalize(recipe, *, source_id, paths, root):
    lines = recipe.split(chr(10))
    end = next((i for i, line in enumerate(lines) if line.startswith('## Change ')), len(lines))
    indexes = [i for i in range(end) if lines[i].startswith('source_id:')]
    changed = False
    if len(indexes) == 1:
        index = indexes[0]
        value = lines[index].partition(':')[2].strip()
        match = re.fullmatch(r'TASK(?:_[0-9]+)?:[ \t]*(.+)', value)
        if match and match[1] in {source_id, source_id.rsplit(':', 1)[1]}:
            lines[index] = 'source_id: ' + source_id
            changed = True
    canonical, proof = previous.canonicalize(chr(10).join(lines), source_id=source_id, paths=paths, root=root)
    proof = dict(proof, original_recipe_sha256=strict.sha(recipe), changed=canonical != recipe,
                 source_task_prefix_normalized=changed or proof['source_task_prefix_normalized'],
                 frame_compiler='TASK_PINNED_SOURCE_SHORTHAND_V3')
    return canonical, proof
