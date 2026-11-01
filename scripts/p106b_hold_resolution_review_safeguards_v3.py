"""Accept the exact new TASK-header/ID layout while preserving strict binding."""
import re
from scripts import p106b_hold_resolution_review_safeguards_v2 as previous

STRUCTURAL_TASK_ID = re.compile(
    r"\A#[ \t]+TASK_[0-9]{3}\n((?:expanded_train|historical_train|validation):[0-9]+)\n"
    r"START_HERE[^\n]*\n")


def __getattr__(name):
    return getattr(previous, name)


def explicit_task_ids(text):
    try:
        return previous.explicit_task_ids(text)
    except ValueError:
        match = STRUCTURAL_TASK_ID.match(text)
        if match is None:
            raise
        return {previous.canonical_id(match[1])}


def review_row_matches_task(source_id, task_text):
    return source_id in explicit_task_ids(task_text)
