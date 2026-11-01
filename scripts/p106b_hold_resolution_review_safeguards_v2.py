#!/usr/bin/env python3
"""Also bind each new review row to its explicit TASK source list."""
import re
from scripts import p106b_hold_resolution_review_safeguards_v1 as previous


def __getattr__(name):
    return getattr(previous, name)


def explicit_task_ids(text):
    result = set()
    for line in text.splitlines():
        match = re.fullmatch(r"#{1,6}[ \t]+((?:expanded_train|historical_train|validation)[:_][0-9]+)[ \t]*", line)
        if match:
            result.add(previous.canonical_id(match[1]))
    if not result:
        raise ValueError("TASK_HAS_NO_EXPLICIT_SOURCE_IDS")
    return result


def review_row_matches_task(source_id, task_text):
    return source_id in explicit_task_ids(task_text)
