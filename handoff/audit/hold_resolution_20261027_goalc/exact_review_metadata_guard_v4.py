"""Add one exact body-free actual-filter case; keep all frozen receipt checks."""
from pathlib import Path
import re
import exact_review_metadata_guard_v3 as legacy
import active_guard_v6_preflight_v1 as guard

AUDIT = Path(__file__).resolve().parent
ROOT = guard.ROOT
inv = guard.inv
_load = legacy.load_receipts
_sources = legacy.validate_sources
_review = legacy.validate_review
_materialize = legacy.materialize_metadata_only
_observer = legacy.install_open_observer


def load_receipts(contract):
    receipts = _load(contract)
    path = AUDIT/'ROOT_360211_METADATA_ONLY_NONADMISSION_V1.json'
    receipt = inv.cache.read(path)
    assert receipt['id'] == guard.NEW_ID and receipt['guard']['sha256'] == guard.EXPECTED
    assert receipt['root_hold_disposition_approved'] is True
    assert receipt['body_admission_approved'] is False
    for label in ['author_review', 'sidecar', 'manifest']:
        assert inv.file_sha(ROOT/receipt[label]['path']) == receipt[label]['sha256']
    receipts[guard.NEW_ID] = dict(receipt,receipt_pin=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)))
    return receipts


def validate_sources(sources, contract, cohort, receipts):
    current = guard.checked_contract()
    entry = current['actual_filter_metadata_hold']
    rest, special = {}, set()
    for key, source in sources.items():
        is_new = key in entry['parent_alias_ids'] or any(source[name]['sha256'] == entry['original']['sha256']
                                                       for name in ['original', 'candidate'])
        if not is_new:
            if not legacy.restricted(source,contract):
                guard.require_payload_context(source,current)
            rest[key] = source
            continue
        assert key == guard.NEW_ID and cohort == entry['cohort']
        receipt = receipts[key]
        assert source['role'] == entry['role'] == receipt['role']
        assert source['original'] == entry['original'] == receipt['original']
        assert source['candidate'] == entry['derived_candidate'] == receipt['candidate']
        assert source['occurrences'] == entry['occurrences'] == receipt['occurrences'] == 2
        trusted = current['trusted_metadata'][key]
        for name in ['source','split','source_ids','source_ids_sha256','input_ids','original_text_sha256']:
            assert source[name] == trusted[name]
        special.add(key)
    return _sources(rest,contract,cohort,receipts) | special


def validate_review(row,receipts):
    if row['id'] != guard.NEW_ID:
        return _review(row,receipts)
    receipt = receipts[row['id']]
    assert row['decision'] == 'NEEDS_ROOT'
    assert all(row['review'][name] == receipt['author_review'][name] for name in ['path','sha256'])
    assert not row.get('body') and not row.get('clean_text_sha256') and not row.get('body_references')
    assert not re.search(r'\.txt\b',row.get('declared_output_cell',''),re.I)


def materialize_metadata_only(row,source,receipts):
    if row['id'] != guard.NEW_ID:
        return _materialize(row,source,receipts)
    validate_review(row,receipts)
    row.update(status='TEXT_ADJUDICATION_NOT_ADMISSION',original=source['original'],
        candidate_metadata=source['candidate'],metadata_only=True,
        metadata_only_receipt=receipts[row['id']]['receipt_pin'],protected_payload_opened=False,
        actual_filter_block=True,individual_human_full_read_completed=False,
        root_approved=False,cache_admitted=False)


def install_open_observer(root,contract):
    _observer(root,contract)
    guard.activate()
    return guard.ATTEMPTS
