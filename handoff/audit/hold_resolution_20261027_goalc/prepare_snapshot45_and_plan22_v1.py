"""Freeze the two final follow-ups in a new snapshot, preserving snapshot44."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
for origin, destination, replacements in [
    ('collect_supplemental_candidates_v44.py', 'collect_supplemental_candidates_v45.py', [
        ('supplemental_candidates_snapshot_v44.json', 'supplemental_candidates_snapshot_v45.json')]),
    ('materialize_reviewed_selection_plan_v21.py', 'materialize_reviewed_selection_plan_v22.py', [
        ('reviewed_selection_plan_v21.json', 'reviewed_selection_plan_v22.json'),
        ('supplemental_candidates_snapshot_v44.json', 'supplemental_candidates_snapshot_v45.json')])
]:
    source = (AUDIT / origin).read_text(encoding='utf-8')
    for before, after in replacements:
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    target = AUDIT / destination
    compile(source, str(target), 'exec')
    with target.open('x', encoding='utf-8') as stream:
        stream.write(source)
    print(target.name)
