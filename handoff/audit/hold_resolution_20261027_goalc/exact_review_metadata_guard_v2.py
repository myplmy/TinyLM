"""Fail closed before payload access; one exact source can remain metadata-only."""
from pathlib import Path
import re

KNOWN_ID = 'expanded_train:28876'
KNOWN_COHORT = 'remaining_field_title_page_004_counter_v1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def restricted(source, contract):
    return (source['id'] in set(contract['restricted_ids']) or
            any(source[label]['sha256'] in set(contract['restricted_hashes'])
                for label in ('original', 'candidate')))


def validate_sources(sources, contract, cohort, receipt):
    """Use only metadata. Unknown protected ID/hash never becomes an exception."""
    metadata_only = set()
    for key, source in sources.items():
        require(key == source['id'], 'source key and ID differ')
        if not restricted(source, contract):
            continue
        require(key == KNOWN_ID and cohort == KNOWN_COHORT,
                'restricted source is outside the exact metadata-only case')
        entry = contract['new_restricted_entry']
        trusted = contract['trusted_metadata'][key]
        require(receipt['id'] == entry['id'] == key and receipt['cohort'] == cohort,
                'metadata-only receipt identity differs')
        require(source['role'] == receipt['role'] == 'context_controls',
                'metadata-only author role differs')
        require(receipt['root_hold_disposition_approved'] is True and
                receipt['body_admission_approved'] is False and
                receipt['decision'] == 'NEEDS_ROOT', 'metadata-only HOLD is not approved')
        require(source['original'] == receipt['original'] == entry['original'],
                'restricted original metadata differs')
        require(source['candidate'] == receipt['candidate'] == entry['derived_candidate'],
                'restricted candidate metadata differs')
        require(source['occurrences'] == receipt['occurrences'] == entry['occurrences'] == 2,
                'restricted position count differs')
        for name in ('source', 'split', 'source_ids', 'source_ids_sha256',
                     'input_ids', 'original_text_sha256'):
            require(source[name] == trusted[name], 'restricted lineage metadata differs')
        metadata_only.add(key)
    return metadata_only


def validate_review(row, receipt):
    require(row['id'] == receipt['id'], 'metadata-only review ID differs')
    require(row['decision'] == 'NEEDS_ROOT' and row['original_status'] in {'NEEDS_ROOT', 'HOLD'},
            'protected source cannot be edited, accepted or excluded through body materialization')
    require(all(row['review'][name] == receipt['author_review'][name]
                for name in ('path', 'sha256')), 'metadata-only review pin differs')
    require(not row.get('body_references') and
            not re.search(r'\.txt\b', row.get('declared_output_cell', ''), re.I),
            'metadata-only HOLD must not declare a training TXT')
    require(not row.get('body') and not row.get('clean_text_sha256'),
            'metadata-only row unexpectedly has a body')


def materialize_metadata_only(row, source, receipt):
    validate_review(row, receipt)
    row.update(status='TEXT_ADJUDICATION_NOT_ADMISSION', original=source['original'],
               candidate_metadata=source['candidate'], metadata_only=True,
               metadata_only_receipt=receipt['receipt_pin'],
               protected_payload_opened=False, root_approved=False, cache_admitted=False)


def install_open_observer(root, contract):
    """A process-local diagnostic, not an OS access-control claim."""
    import sys
    numbers = {key.rsplit(':', 1)[1] for key in contract['restricted_ids']}
    hashes = {key.lower() for key in contract['restricted_hashes']}
    exact_paths = {(root / contract['new_restricted_entry'][name]['path']).resolve()
                   for name in ('original', 'derived_candidate')}
    attempted = []

    def observe(event, args):
        if event != 'open' or not args or not isinstance(args[0], (str, bytes, Path)):
            return
        path = Path(args[0].decode() if isinstance(args[0], bytes) else args[0])
        resolved = path.resolve()
        matched = resolved in exact_paths
        if path.suffix.lower() == '.txt':
            matched = matched or path.stem.lower() in hashes or any(
                re.search(r'(?:^|[_:/])' + re.escape(number) + r'(?:[_./]|$)', str(path))
                for number in numbers)
        if matched:
            attempted.append(str(path))
            raise PermissionError('protected payload open denied before reading')

    sys.addaudithook(observe)
    return attempted
