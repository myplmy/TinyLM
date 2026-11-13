"""Extend immutable snapshot verification to independently recovered historical evidence."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
old = json.loads((OUT / 'SNAPSHOT_LINK_BASE_AUDIT_v2.json').read_text())
pending = json.loads((OUT / 'OWN_PENDING_RECONCILIATION_v1.json').read_text())
names = sorted({r['snapshot'] for r in old['snapshots']} | {
    r['path'] for r in pending['owned_pending'] if r['path'].endswith('/initial_plan.md')})
assert len(names) == 13
rows = []
for name in names:
    path = ROOT / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    profile_path = path.with_name('profile.json')
    profile = json.loads(profile_path.read_text())
    field = 'plan_sha256' if 'plan_sha256' in profile else 'initial_plan_sha256'
    assert profile[field].upper() == digest, name
    links = []
    for raw in re.findall(r'\]\(([^)#][^)]*?)\)',path.read_text()):
        target = raw.split('#')[0].strip()
        if not target or target.startswith(('https://','http://','mailto:')) or '{' in target or '...' in target:
            continue
        if not re.search(r'\.(md|txt|py|bat|json|png|pdf|tsv|csv)$',target):
            continue
        original = (ROOT / 'test_plan' / target).resolve()
        relative = original.relative_to(ROOT).as_posix()
        assert not relative.startswith('datasets/'), relative
        assert original.is_file(), (name,relative)
        links.append(dict(relative_as_original=target,original_base_target=relative,
            current_copy_resolves=(path.parent / target).is_file()))
    rows.append(dict(snapshot=name,sha256=digest,profile=profile_path.relative_to(ROOT).as_posix(),
        profile_field=field,links=links))
source_root = ROOT / 'handoff/audit/nov05_gsq_objective/source_snapshot_v1'
source_manifest = json.loads((source_root / 'manifest.json').read_text())
for row in source_manifest['files']:
    assert hashlib.sha256((source_root / row['path']).read_bytes()).hexdigest().upper() == row['sha256']
value = dict(schema='NOV13_IMMUTABLE_SNAPSHOT_LINK_BASE_V3',status='ORIGINAL_BASE_VERIFIED',
    snapshots=rows,snapshot_count=len(rows),link_count=sum(len(r['links']) for r in rows),
    archived_source_files_verified=len(source_manifest['files']),
    note='Original bytes and shared checker unchanged. Historical raw copies remain in Git; live documentation scope excludes exactly these SHA-pinned plan copies.')
with (OUT / 'SNAPSHOT_LINK_BASE_AUDIT_v3.json').open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps(dict(snapshots=len(rows),links=value['link_count'],archived_sources=len(source_manifest['files']))))
