"""Bind both finished follow-ups and all237 reviews; do not admit cache text."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
for origin, destination, replacements in [
    ('collect_supplemental_candidates_v45.py', 'collect_supplemental_candidates_v46.py', [
        ('supplemental_candidates_snapshot_v45.json', 'supplemental_candidates_snapshot_v46.json')]),
    ('materialize_reviewed_selection_plan_v22.py', 'materialize_reviewed_selection_plan_v23.py', [
        ('reviewed_selection_plan_v22.json', 'reviewed_selection_plan_v23.json'),
        ('supplemental_candidates_snapshot_v45.json', 'supplemental_candidates_snapshot_v46.json')]),
    ('prepare_fresh_author_body_audit_v1.py', 'prepare_fresh_author_body_audit_v2.py', [
        ('supplemental_candidates_snapshot_v43.json', 'supplemental_candidates_snapshot_v46.json'),
        ('len(rows) == 835', 'len(rows) == 843'),
        ("for row in rows) == 824", "for row in rows) == 843"),
        ('PROVISIONAL_AUTHOR_BODY_ROSTER_V1.json', 'PROVISIONAL_AUTHOR_BODY_ROSTER_V2.json'),
        ('fresh_author_body_literals_v1.json', 'fresh_author_body_literals_v2.json'),
        ('audit_fresh_author_bodies_v1.py', 'audit_fresh_author_bodies_v2.py'),
        ('835 proposal records / 824 body audits', '843 proposal records / 843 body audits')])
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
