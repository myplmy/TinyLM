"""Keep a raw binding rejection explicit; never supply an accepted body."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def quarantine_rejected_row(row, source, raw_errors):
    require(row.get('id') == source['id'] and row.get('role') == source['role'],
            'raw review/source identity or role changed')
    original = source['original']
    if 'original' in row:
        require(row['original'] == original, 'raw source binding changed')
    if row.get('status') != 'MECHANICAL_REJECTION_NOT_APPLIED':
        require('original' in row, 'non-rejected raw row lacks original source pin')
        return None

    review = row.get('review')
    require(isinstance(review, dict) and review.get('path') and review.get('sha256'),
            'raw rejection lacks an exact review pin')
    matches = [error for error in raw_errors if error.get('id') == row['id']
               and error.get('role') == row['role'] and error.get('review') == review]
    require(len(matches) == 1 and matches[0].get('error')
            and matches[0]['error'] == row.get('error'),
            'raw rejection does not match its exact recorded error')
    # Only source/review identity and failure metadata survive this boundary.
    # A partially materialized body cannot leak through a negative record.
    result = {key: row[key] for key in ('id', 'role', 'cohort', 'review') if key in row}
    result.update(original=dict(original),
                  status='BLOCKED_BY_RAW_MECHANICAL_REJECTION',
                  raw_snapshot_status=row['status'], raw_review_error=row['error'],
                  original_pin_from_source_manifest='original' not in row,
                  root_approved=False, cache_admitted=False,
                  input_delivery=dict(status='RAW_REVIEW_BINDING_REJECTED_NOT_DELIVERY_APPROVED'))
    return result
