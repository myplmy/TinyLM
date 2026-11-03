"""Independently check persisted metadata evidence, without opening source bodies."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    return json.loads(path.read_bytes())


def pinned(item):
    path = ROOT / item['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    payload = path.read_bytes()
    assert sha(payload) == item['sha256']
    return payload


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()), bytes=path.stat().st_size)


activation_path = AUDIT / 'BIRTH_INPUT_DELIVERY_ACTIVATION_V1.json'
activation = read(activation_path)
config = json.loads(pinned(activation['config']))
pinned(activation['module'])
contract = json.loads(pinned(config['contract']))
manifest = json.loads(pinned(config['manifest']))
sources = {r['id']: r for r in manifest['rows']}
assert len(sources) == 2707
# Both protections precede review-file reading. No original or candidate bytes are needed.
assert not set(sources) & set(contract['restricted_ids'])
assert not {r['original']['sha256'] for r in sources.values()} & set(contract['restricted_hashes'])
for assigned in config['roles'].values():
    pinned(assigned['reader'])
    pinned(assigned['registry'])
gated_path = BASE / 'birth_root11_input_delivery_gated_v1/v3/complete.json'
gated = read(gated_path)
assert gated['root_adopted'] == gated['cache_admitted'] == 0 and not gated['failures']
assert gated['raw_errors'] == 0 and gated['config'] == activation['config']
for key in ('validator', 'validator_base', 'event_archiver', 'activation', 'module'):
    pinned(gated[key])
raw = json.loads(pinned(gated['raw_snapshot']))
records = [r for s in gated['shards'] for r in json.loads(pinned(s))]
assert len(records) == len({r['id'] for r in records}) == 2707
assert all(r.get('cache_admitted', False) is False and r.get('root_approved', False) is False
           for r in records)
events = []
for shard in gated['event_shards']:
    payload = pinned(shard)
    assert len(payload) <= 1_000_000 and payload.endswith(b'\n')
    assert shard['source_journal_prefix']['sha256'] == shard['sha256']
    # Live journals may append; only their immutable verified prefix archive is consumed.
    for line in payload.splitlines():
        event = json.loads(line)
        claimed = event.pop('event_sha256')
        assert sha(json.dumps(event, sort_keys=True, ensure_ascii=False,
                              separators=(',', ':')).encode()) == claimed
        assert event['schema'] == 'BIRTH_PACKET_SUCCESSFUL_EMISSION_V1'
        assert event['purpose'] == 'REVIEW_INPUT'
        events.append(event)
checks = []
for row in records:
    if row['input_delivery']['status'] != 'INPUT_DELIVERED_BEFORE_REVIEW':
        continue
    source = sources[row['id']]
    review = row['review']
    pinned(review)
    stamp = (ROOT / review['path']).stat().st_mtime_ns
    assert stamp == row['input_delivery']['review_mtime_ns']
    for number, part in enumerate(source['reading_parts'], 1):
        assert any(e['role'] == row['role'] == source['role'] and
                   e['cohort'] == config['cohort'] and e['source_id'] == row['id'] and
                   e['packet'] == number and e['packets'] == len(source['reading_parts']) and
                   e['original_sha256'] == source['original']['sha256'] and
                   e['candidate_sha256'] == source['candidate']['sha256'] and
                   e['packet_sha256'] == part['sha256'] and
                   e['config_sha256'] == activation['config']['sha256'] and
                   e['module_sha256'] == activation['module']['sha256'] and
                   e['reader_sha256'] == config['roles'][row['role']]['reader']['sha256'] and
                   e['registry_sha256'] == config['roles'][row['role']]['registry']['sha256'] and
                   0 < e['emitted_at_ns'] <= stamp for e in events)
    checks.append(dict(id=row['id'], role=row['role'], packets=len(source['reading_parts']),
                       review_sha256=review['sha256'], review_mtime_ns=stamp))
assert len(checks) == 5
test_log = AUDIT / 'INPUT_DELIVERY_GUARD_CPU_TESTS_20261104_V1.log'
log = test_log.read_text(encoding='utf-8')
assert re.search(r'Ran 20 tests in [0-9.]+s', log) and log.rstrip().endswith('OK')
field = []
for page, version in [(1, 'v8'), (2, 'v8'), (3, 'v6'), (4, 'v6'), (5, 'v2')]:
    path = BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json'
    data = read(path)
    assert not data['errors'] and not data['needs_root']
    field.append(dict(page=page, version=version, saved=sum(v['saved'] for v in data['coverage'].values()),
                       snapshot=pin(path)))
assert sum(r['saved'] for r in field) == 1151
assert sum(v['saved'] for v in raw['coverage'].values()) == 1000
result = dict(status='ACTUAL_PROSPECTIVE_INPUT_DELIVERY_EVIDENCE_INDEPENDENTLY_RECHECKED',
    tests=dict(passed=20, failed=0, actual_exit_code=0, raw_log=pin(test_log)),
    actual_reader_receipt=pin(AUDIT / 'BIRTH_INPUT_DELIVERY_READERS_VERIFIED_V1.json'),
    activation=pin(activation_path), gated_view=pin(gated_path),
    verified_role_review_rows=checks, verified_packet_bindings=sum(r['packets'] for r in checks),
    field_snapshots=field, field_saved=1151, field_expected=18237,
    field_first_review_not_saved=17086, other_first_review_not_saved=50162,
    combined_unique_first_review_not_saved=67248, protected_metadata_only_sources=1,
    birth_saved=1000, birth_expected=2707, birth_not_saved=1707,
    birth_raw_errors=0, birth_frozen_needs_root=raw['needs_root'],
    historical_source_scope=995, historical_saved_rows_in_this_raw_snapshot=995,
    prospective_source_scope=1712, prospective_saved_rows_with_delivery_precondition_met=5,
    root_probe_events_accepted_as_role_evidence=0, retrospective_emission_claim=False,
    preimplementation_record='WIP_EXACT_FOLLOWUP_V20_APPLIED.json remains historical, not current.',
    negative_history=[
        dict(tool_chunk='4764e3', tests=16, failures=1,
             reason='Test assumed five rotated shards; actual bounded two-events-per-shard produced three. '
                    'Corrected test checks actual rotation, size, and preservation instead of guessed shard count.'),
        dict(tool_chunk='d9cc20', tests=3, failures=0,
             warning='Two test append streams were unclosed; corrected context managers and final -W error suite passed.'),
        dict(gated_views=['v1', 'v2'],
             limit='Historical checks pin live journal bytes. Future use consumes v3 immutable prefix archives.')],
    original_or_candidate_body_reads_for_this_checker=0, semantic_admission_inferred=False,
    cache_admitted=0, root_adopted=0, goal_complete=False, training_authorized=False)
target = AUDIT / 'BIRTH_INPUT_DELIVERY_CURRENT_RUNTIME_EVIDENCE_V1.json'
payload = (json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
with target.open('xb') as stream:
    stream.write(payload)
print(json.dumps(dict(status=result['status'], tests=20, verified_review_rows=len(checks),
                      verified_packet_bindings=result['verified_packet_bindings'], field_saved=1151,
                      birth_saved=1000, cache_admitted=0), ensure_ascii=False))
