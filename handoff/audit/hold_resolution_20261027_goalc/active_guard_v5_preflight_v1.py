"""Check cumulative metadata guard5 and deny all classified payload aliases."""
from pathlib import Path
from guarded_reviewed_cache_v6 import checked_contract as old_contract, ROOT, inv
from exact_review_metadata_guard_v2 import install_open_observer

AUDIT = Path(__file__).resolve().parent
CONTRACT = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json'
EXPECTED = '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338'
NEW_IDS = {'expanded_train:32895','expanded_train:74587'}
ATTEMPTS = None


def checked_contract():
    previous = old_contract()
    assert not CONTRACT.is_symlink() and inv.file_sha(CONTRACT) == EXPECTED
    data = inv.cache.read(CONTRACT)
    assert len(data['restricted_ids']) == 11 and len(data['restricted_hashes']) == 14
    assert len(data['trusted_metadata']) == 19
    assert set(previous['restricted_ids']) < set(data['restricted_ids'])
    assert set(data['restricted_ids'])-set(previous['restricted_ids']) == NEW_IDS
    assert set(previous['restricted_hashes']) < set(data['restricted_hashes'])
    assert all(data['trusted_metadata'][key] == value for key,value in previous['trusted_metadata'].items())
    assert data['new_restricted_entry'] == previous['new_restricted_entry']
    assert {r['id'] for r in data['newly_quarantined_entries']} == NEW_IDS
    for item in data['newly_quarantined_entries']:
        assert item['role'] == 'context_controls' and item['occurrences'] == 2
        assert item['body_admission_approved'] is False
        assert len(item['parent_alias_ids']) == 2
        assert all(data['trusted_metadata'][key]['parent_decision'] == 'HOLD'
            and data['trusted_metadata'][key]['original_text_sha256'] == item['original']['sha256']
            for key in item['parent_alias_ids'])
        assert all(item[name]['sha256'] in data['restricted_hashes']
            for name in ['original','derived_candidate'])
    return data


def activate():
    global ATTEMPTS
    if ATTEMPTS is None:
        data = checked_contract()
        diagnostic = dict(data,restricted_ids=sorted(set(data['restricted_ids']) | set(data['trusted_metadata'])))
        ATTEMPTS = install_open_observer(ROOT,diagnostic)
    return EXPECTED


def assert_no_protected_opens():
    assert ATTEMPTS is not None and len(ATTEMPTS) == 0


def validate_new_hold(row, source):
    """Only exact metadata and a body-free NEEDS_ROOT row are accepted."""
    assert row['id'] == source['id'] and row['id'] in NEW_IDS
    data = checked_contract()
    item, = [r for r in data['newly_quarantined_entries'] if r['id'] == row['id']]
    assert source['original'] == item['original'] and source['candidate'] == item['derived_candidate']
    assert source['role'] == item['role'] and source['occurrences'] == item['occurrences']
    assert row['decision'] == 'NEEDS_ROOT'
    assert not row.get('body') and not row.get('clean_text_sha256') and not row.get('body_references')
    assert '.txt' not in row.get('declared_output_cell','').lower()
    return item
