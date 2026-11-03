"""Classify only individually approved exact-source non-admissions as reviewed."""

SCHEMA = 'P106B_REVIEWED_HOLD_PARTITION_V1'


def classify_hold(row, cases):
    if row.get('decision') != 'HOLD':
        raise ValueError('only a non-admitted HOLD may be partitioned')
    if row.get('text') or row.get('clean_text_sha256') or row.get('root_approved') is not False:
        raise ValueError('HOLD cannot contain or approve a training body')
    status = row.get('review_status')
    if status == 'UNRESOLVED_NOT_ADMITTED':
        if row.get('content_reviewed') or row.get('root_disposition_approved') or row.get('hold_review_evidence'):
            raise ValueError('unresolved HOLD cannot claim content review')
        return 'UNPROCESSED'
    if status != 'REVIEWED_NOT_ADMITTED' or row.get('content_reviewed') is not True \
            or row.get('root_disposition_approved') is not True:
        raise ValueError('unknown HOLD review status')
    key = row['original_text_sha256']
    case = cases.get(key)
    if not case or case.get('reviewed') is not True or case.get('root_approved') is not True \
            or case.get('decision') != 'HOLD':
        raise ValueError('reviewed HOLD lacks an exact root source judgment')
    if row.get('id') != case['id'] or row.get('hold_review_evidence') != case['authority_pin']:
        raise ValueError('reviewed HOLD source ID or evidence pin differs')
    return 'REVIEWED_NOT_ADMITTED'


def partition_occurrences(rows, proposals, cases):
    counts = dict(documents=0, input_ids=0, remaining_hold=0, reviewed_hold=0, unprocessed=0)
    seen_ids = set()
    for source in rows:
        if source['id'] in seen_ids:
            raise ValueError('a source position is repeated')
        seen_ids.add(source['id'])
        counts['documents'] += 1
        counts['input_ids'] += source['input_ids']
        proposal = proposals[source['original_text_sha256']]
        if proposal['decision'] == 'HOLD':
            kind = classify_hold(proposal, cases)
            counts['remaining_hold'] += 1
            counts['reviewed_hold' if kind == 'REVIEWED_NOT_ADMITTED' else 'unprocessed'] += 1
    if counts['remaining_hold'] != counts['reviewed_hold'] + counts['unprocessed']:
        raise ValueError('HOLD partition does not conserve source positions')
    return counts
