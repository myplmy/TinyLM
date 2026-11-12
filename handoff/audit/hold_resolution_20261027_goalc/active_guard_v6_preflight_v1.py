"""Exact metadata-only extension for one actual content-filter block."""
from pathlib import Path
import active_guard_v5_preflight_v1 as previous
from exact_review_metadata_guard_v2 import install_open_observer

AUDIT = Path(__file__).resolve().parent
ROOT = previous.ROOT
inv = previous.inv
CONTRACT = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V6.json'
EXPECTED = '5AAFF02F7B2709C06843221FBE39C700909685809FA845253B6A749553721C0E'
NEW_ID = 'expanded_train:360211'
NEW_ALIAS = 'historical_train:360215'
_previous_checked = previous.checked_contract
_previous_activate = previous.activate
_previous_assert = previous.assert_no_protected_opens
ATTEMPTS = None


def checked_contract():
    old = _previous_checked()
    assert not CONTRACT.is_symlink() and inv.file_sha(CONTRACT) == EXPECTED
    data = inv.cache.read(CONTRACT)
    assert set(data['restricted_ids']) - set(old['restricted_ids']) == {NEW_ID, NEW_ALIAS}
    assert len(data['restricted_hashes']) == 25 and len(data['trusted_metadata']) == 21
    assert all(data['trusted_metadata'][key] == value for key,value in old['trusted_metadata'].items())
    entry = data['actual_filter_metadata_hold']
    assert entry['id'] == NEW_ID and entry['role'] == 'legacy_review'
    assert entry['body_admission_approved'] is False and entry['occurrences'] == 2
    assert set(entry['parent_alias_ids']) == {NEW_ID, NEW_ALIAS}
    assert entry['original']['sha256'] == entry['derived_candidate']['sha256']
    new_hashes = {entry['original']['sha256']} | {p['sha256'] for p in entry['reading_parts']}
    assert set(data['restricted_hashes']) - set(old['restricted_hashes']) == new_hashes
    for key in entry['parent_alias_ids']:
        trusted = data['trusted_metadata'][key]
        assert trusted['parent_decision'] == 'HOLD'
        assert trusted['original_text_sha256'] == entry['original']['sha256']
    return data


def activate():
    global ATTEMPTS
    if ATTEMPTS is None:
        _previous_activate()
        data = checked_contract()
        diagnostic = dict(data, restricted_ids=sorted(set(data['restricted_ids']) | set(data['trusted_metadata'])))
        ATTEMPTS = install_open_observer(ROOT, diagnostic)
    return EXPECTED


def assert_no_protected_opens():
    _previous_assert()
    assert ATTEMPTS is not None and len(ATTEMPTS) == 0


def require_payload_context(context, contract=None):
    """Metadata rejection occurs before load_pair or any body hashing."""
    data = checked_contract() if contract is None else contract
    ident = context.get('source_id', context.get('id'))
    if ident in set(data['restricted_ids']) | set(data['trusted_metadata']):
        raise ValueError('restricted source identity; metadata-only HOLD')
    for name in ['original', 'candidate']:
        if context[name]['sha256'] in set(data['restricted_hashes']):
            raise ValueError('restricted payload SHA alias; metadata-only HOLD')


def install_for_legacy():
    """Retain frozen modules and make future metadata skip checks cumulative."""
    activate()
    previous.checked_contract = checked_contract
    previous.activate = activate
    previous.assert_no_protected_opens = assert_no_protected_opens

