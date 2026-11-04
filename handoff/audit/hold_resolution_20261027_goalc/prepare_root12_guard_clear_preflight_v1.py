"""Prepare exact candidates from completed reviews; do not grant admission."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
VERSIONS = {1:'v20',2:'v16',3:'v14',4:'v14',5:'v12',6:'v15',7:'v15',8:'v13',9:'v7',10:'v1'}
pins = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    value = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(value).hexdigest().upper()
    return json.loads(value)


guard_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'
assert sha(guard_path) == 'E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B'
guard = read(guard_path)
previous = read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')
prior_ids = {row['id'] for row in previous['rows']}
prior_hashes = {row['original_text_sha256'] for row in previous['rows']}
current = {}
cohorts = [('remaining_field_title_page_'+str(page).zfill(3)+'_counter_v1',version)
           for page,version in VERSIONS.items()]
cohorts += [('remaining_literal_full_counter_v1','v21')]
for cohort,version in cohorts:
    manifest = read(BASE/cohort/'manifest.json')
    sources = {row['id']:row for row in manifest['rows']}
    path = BASE/(cohort+'_snapshots')/version/'complete.json'
    summary = read(path)
    assert not summary['errors']
    for pin in summary['shards']:
        shard = ROOT/pin['path']
        assert sha(shard) == pin['sha256']
        for row in read(shard):
            assert row['id'] not in current
            current[row['id']] = dict(record=row,source=sources[row['id']],snapshot=dict(
                path=str(path.relative_to(ROOT)),sha256=sha(path)))

rows = []
deferred = []
counts = Counter()
seen = set()
for name in ('FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V3.json',
             'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'):
    diagnostic_path = AUDIT/name
    diagnostic = read(diagnostic_path)
    for pin in diagnostic['shards']:
        path = ROOT/pin['path']
        assert sha(path) == pin['sha256']
        for check in read(path):
            key = check['id']
            assert key not in seen
            seen.add(key)
            if key in prior_ids:
                deferred.append(dict(id=key,reason='ALREADY_IN_PRIOR_ROOT'))
                continue
            chosen = current[key]
            record,source = chosen['record'],chosen['source']
            if not all(check['guards'].values()):
                deferred.append(dict(id=key,reason='INDIVIDUAL_DIAGNOSTIC_FLAGS',
                                     flags=[k for k,v in check['guards'].items() if not v]))
                continue
            if (record.get('body') != check['body']['path'] or
                record.get('clean_text_sha256') != check['body']['sha256'] or
                source['original'] != check['original']):
                deferred.append(dict(id=key,reason='CURRENT_EXACT_SOURCE_BODY_PAIR_CHANGED'))
                continue
            assert record['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION','MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
            assert source['id'] not in guard['restricted_ids']
            assert all(source[label]['sha256'] not in guard['restricted_hashes']
                       for label in ('original','candidate'))
            assert check['body']['sha256'] not in guard['restricted_hashes']
            assert source['original']['sha256'] not in prior_hashes
            assert record['read_scope'] and record['review_source_format'].startswith('EXPLICIT_')
            original,body = ROOT/source['original']['path'],ROOT/record['body']
            assert original.resolve().is_relative_to(BASE) and body.resolve().is_relative_to(BASE)
            assert not original.is_symlink() and not body.is_symlink()
            assert sha(original) == source['original']['sha256']
            assert sha(body) == record['clean_text_sha256']
            author_review = ROOT/record['review']['path']
            assert sha(author_review) == record['review']['sha256']
            row = dict(id=key,cohort=record['cohort'],role=record['role'],
                original=source['original'],candidate=source['candidate'],
                original_text_sha256=source['original_text_sha256'],
                source_ids=source['source_ids'],source_ids_sha256=source['source_ids_sha256'],
                input_ids=source['input_ids'],occurrences=source['occurrences'],
                body=check['body'],review=record['review'],read_scope=record['read_scope'],
                author_output=record.get('author_output'),reason=record['reason'],
                source_context_review=record['review'],snapshot=chosen['snapshot'],
                diagnostics=dict(path=str(diagnostic_path.relative_to(ROOT)),sha256=sha(diagnostic_path)),
                guards=check['guards'],root_approved=False,cache_admitted=False,
                independent_semantic_admission_review='PENDING')
            rows.append(row)
            counts.update(sources=1,positions=source['occurrences'])
            counts[record['cohort']] += 1
assert len(rows) == len({row['id'] for row in rows}) == len({row['original_text_sha256'] for row in rows})
assert len(rows)+len(deferred) == len(seen)
directory = BASE/'root12_guard_clear_preflight_v1'
directory.mkdir(exist_ok=False)
payload = (json.dumps(rows,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
assert len(payload)<20_000_000
with (directory/'records_000.json').open('xb') as stream: stream.write(payload)
summary = dict(status='EXACT_GUARD_CLEAR_CANDIDATES_NOT_ROOT_ADMISSION',
    recorded_at=datetime.now(timezone.utc).isoformat(),counts=dict(counts),
    records=dict(path=str((directory/'records_000.json').relative_to(ROOT)),
                 sha256=sha(directory/'records_000.json'),bytes=len(payload)),
    diagnostic_body_rows=len(seen),deferred_count=len(deferred),deferred=deferred,
    input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}),
    guard_failures_waived=0,protected_original_or_candidate_TXT_opens=0,
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False)
for path in (directory/'complete.json',AUDIT/'ROOT12_GUARD_CLEAR_PREFLIGHT_V1.json'):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(summary,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))
print(json.dumps(dict(status=summary['status'],counts=dict(counts),deferred=len(deferred),
    receipt_sha256=sha(AUDIT/'ROOT12_GUARD_CLEAR_PREFLIGHT_V1.json')),ensure_ascii=False))
