"""Keep old exact HOLD rules; defer the new protected submission without payload IO."""
from pathlib import Path
from exact_review_metadata_guard_v2 import (restricted, validate_sources as old_sources,
    validate_review as old_review, materialize_metadata_only as old_materialize, require)
from guarded_reviewed_cache_v6 import ROOT, inv, checked_contract, EXPECTED
import active_guard_v4_preflight_v1 as current

AUDIT = Path(__file__).resolve().parent
NEW_ID = 'expanded_train:267902'


def load_receipts(contract):
    require(contract == checked_contract(), 'active guard4 differs')
    old_path = AUDIT/'ROOT_28876_METADATA_ONLY_NONADMISSION_V1.json'
    require(inv.file_sha(old_path) == '99DB56A82E4215B21A7A4783C4B74E75886467C8DD6678A1F1A2C0CE90AEA7A2', 'old receipt changed')
    paths = [old_path, AUDIT/'ROOT_267902_METADATA_ONLY_NONADMISSION_V1.json']
    output = {}
    for path in paths:
        receipt = inv.cache.read(path)
        for label in ['author_review', 'manifest']:
            require(inv.file_sha(ROOT/receipt[label]['path']) == receipt[label]['sha256'], 'metadata review or manifest changed')
        if 'sidecar' in receipt:
            require(inv.file_sha(ROOT/receipt['sidecar']['path']) == receipt['sidecar']['sha256'], 'old sidecar changed')
        output[receipt['id']] = dict(receipt, receipt_pin=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path)))
    require(output[NEW_ID]['guard']['sha256'] == EXPECTED, 'new receipt requires current guard4')
    return output


def validate_sources(sources, contract, cohort, receipts):
    metadata_only = set()
    for key, source in sources.items():
        require(key == source['id'], 'source identity differs')
        if not restricted(source, contract): continue
        require(key in receipts, 'protected source has no exact metadata-only case')
        receipt = receipts[key]
        if key != NEW_ID:
            old_contract_path = ROOT/receipt['guard']['path']
            require(inv.file_sha(old_contract_path) == receipt['guard']['sha256'], 'frozen old guard changed')
            old = inv.cache.read(old_contract_path)
            old_sources({key: source}, dict(contract, new_restricted_entry=old['new_restricted_entry']), cohort, receipt)
        else:
            entry = contract['new_restricted_entry']; trusted = contract['trusted_metadata'][key]
            require(cohort == receipt['cohort'] and source['role'] == receipt['role'] == 'historical_review', 'new metadata-only cohort or role differs')
            require(receipt['root_hold_disposition_approved'] is True and receipt['body_admission_approved'] is False, 'new body was admitted without safe-view proof')
            require(source['original'] == receipt['original'] == entry['original'] and
                source['candidate'] == receipt['candidate'] == entry['derived_candidate'], 'new protected source pins differ')
            require(source['occurrences'] == receipt['occurrences'] == entry['occurrences'] == 2, 'new occurrence count differs')
            for name in ['id','source','split','source_ids','source_ids_sha256','input_ids','original_text_sha256']:
                require(source[name] == trusted[name], 'new frozen parent identity differs')
        metadata_only.add(key)
    return metadata_only


def validate_review(row, receipts):
    receipt = receipts[row['id']]
    if row['id'] != NEW_ID: return old_review(row, receipt)
    require(all(row['review'][name] == receipt['author_review'][name] for name in ['path','sha256']), 'new protected author review changed')
    require(not row.get('body') and not row.get('clean_text_sha256'), 'protected payload was materialized')


def materialize_metadata_only(row, source, receipts):
    receipt = receipts[row['id']]
    if row['id'] != NEW_ID: return old_materialize(row, source, receipt)
    validate_review(row, receipts)
    row.update(authored_decision_before_metadata_nonadmission=row['decision'],
        authored_declared_output_cell=row.get('declared_output_cell'),
        authored_body_references=row.get('body_references', []),
        decision='NEEDS_ROOT', declared_output_cell='—', body_references=[],
        status='TEXT_ADJUDICATION_NOT_ADMISSION', original=source['original'],
        candidate_metadata=source['candidate'], metadata_only=True,
        metadata_only_receipt=receipt['receipt_pin'], protected_payload_opened=False,
        safe_partial_submission_unadmitted=True, root_approved=False, cache_admitted=False)


def install_open_observer(root, contract):
    require(root == ROOT and contract == checked_contract(), 'observer requires current contract')
    current.activate()
    return current.ATTEMPTS
