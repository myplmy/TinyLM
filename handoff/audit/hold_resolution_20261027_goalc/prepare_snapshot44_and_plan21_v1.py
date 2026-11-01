"""Collect all reported final237 reviews while preserving every older snapshot."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
for origin, destination, replacements in [
    ('collect_supplemental_candidates_v43.py', 'collect_supplemental_candidates_v44.py', [
        ('supplemental_candidates_snapshot_v43.json', 'supplemental_candidates_snapshot_v44.json')]),
    ('materialize_reviewed_selection_plan_v20.py', 'materialize_reviewed_selection_plan_v21.py', [
        ('reviewed_selection_plan_v20.json', 'reviewed_selection_plan_v21.json'),
        ('supplemental_candidates_snapshot_v43.json', 'supplemental_candidates_snapshot_v44.json')])
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
