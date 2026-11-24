"""Indexed ACTD alignment for the original native-prefix position format."""

from bisect import bisect_left, bisect_right
from collections import defaultdict

from scripts.p106b_actd_anchor import _boundaries
from scripts.p106b_actd_cache import POLICIES


def prefix_triplets(rows):
    return [(row["character_end"], row["owner"], row["prefix_raw_index"]) for row in rows]


def choose(chars, indices, minimum_index, student_char, policy):
    first = bisect_left(indices, minimum_index)
    if policy == "causal_left_variant":
        after = bisect_right(chars, student_char, lo=first)
        return bisect_left(chars, chars[after - 1], lo=first) if after > first else None
    following = bisect_left(chars, student_char, lo=first)
    if following == first:
        return following if following < len(chars) else None
    left = following - 1
    if following < len(chars) and chars[following] - student_char < student_char - chars[left]:
        return following
    return bisect_left(chars, chars[left], lo=first)


def align_positions(student, teacher, *, policy):
    """Preserve matches and holds for native records with monotonic prefix metadata."""
    if policy not in POLICIES:
        raise ValueError("explicit ACTD alignment policy required")
    if len({row["prefix_raw_index"] for row in teacher}) != len(teacher):
        raise ValueError("unique teacher predictor positions required")
    students, teachers = _boundaries(prefix_triplets(student)), _boundaries(prefix_triplets(teacher))
    by_owner = defaultdict(list)
    for (char, owner, idx), row in zip(teachers, teacher, strict=True):
        by_owner[owner].append((char, idx, row))
    index = {owner: tuple(zip(*entries)) for owner, entries in by_owner.items()}
    rows, holds = [], []
    previous = -1
    for (char, owner, student_index), source in zip(students, student, strict=True):
        chars, indices, values = index.get(owner, ((), (), ()))
        selected = choose(chars, indices, previous, char, policy)
        if selected is None:
            holds.append(dict(student_target_raw_index=source["target_raw_index"],
                reason="NO_SAME_OWNER_MONOTONIC_PREFIX", policy=policy))
            continue
        previous = indices[selected]
        chosen_char = chars[selected]
        target = values[selected]
        rows.append(dict(student_prefix_raw_index=student_index, teacher_prefix_raw_index=previous,
            student_character_end=char, teacher_character_end=chosen_char, owner=owner,
            lookahead_characters=max(0, chosen_char-char), backtrack_characters=max(0, char-chosen_char),
            policy=policy, student_target_raw_index=source["target_raw_index"], student_target_id=source["target_id"],
            teacher_target_raw_index=target["target_raw_index"], teacher_target_id=target["target_id"]))
    return rows, holds
