"""Audit saved new reviews as proposals, without granting root approval."""
from pathlib import Path
import hashlib
import json

AUDIT = Path(__file__).resolve().parent
snapshot_path = AUDIT / 'supplemental_candidates_snapshot_v43.json'
snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
groups = {'root_selected_lexical_counter_v1', 'ordinal_metadata_counter_v26_v1',
          'profile_strata_source_counter_v25_v1'}
rows = []
for record in snapshot['records']:
    if record['cohort'] not in groups:
        continue
    rows.append(dict(id=record['id'], original_text_sha256=record['original']['sha256'],
        original_paths=[record['original']['path']], selected=dict(record)))
assert len(rows) == 835 and sum(bool(row['selected'].get('body')) for row in rows) == 824
roster = dict(status='SAVED_AUTHOR_PROPOSALS_LITERAL_AUDIT_INPUT_NOT_ROOT_SELECTION', rows=rows,
    snapshot=dict(path=str(snapshot_path.relative_to(AUDIT.parents[2])),
                  sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest().upper()),
    root_approved=False, cache_admitted=0, goal_complete=False)
roster_path = AUDIT / 'PROVISIONAL_AUTHOR_BODY_ROSTER_V1.json'
with roster_path.open('x', encoding='utf-8') as stream:
    json.dump(roster, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
source = (AUDIT / 'audit_root_selected_bodies_v5.py').read_text(encoding='utf-8')
for before, after in [
    ('p106b_hold_resolution_policy_v25', 'p106b_hold_resolution_policy_v26'),
    ('root_selected_body_literals_v5.json', 'fresh_author_body_literals_v1.json'),
    ('ROOT_AUTHORED_SELECTIONS_V9.json', 'PROVISIONAL_AUTHOR_BODY_ROSTER_V1.json')
]:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
target = AUDIT / 'audit_fresh_author_bodies_v1.py'
compile(source, str(target), 'exec')
with target.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared 835 proposal records / 824 body audits, approval remains false.')
