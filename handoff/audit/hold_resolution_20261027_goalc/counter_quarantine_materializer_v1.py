"""Route exact new HOLDs around the legacy payload materializer."""
from active_guard_v5_preflight_v1 import NEW_IDS,EXPECTED,validate_new_hold


def materialize(row,source,directory,unrestricted):
    if row['id'] not in NEW_IDS:
        return unrestricted(row,source,directory)
    validate_new_hold(row,source)
    row.update(status='TEXT_ADJUDICATION_NOT_ADMISSION',original=source['original'],
        candidate_metadata=source['candidate'],metadata_only=True,
        active_quarantine_contract_sha256=EXPECTED,protected_payload_opened=False,
        root_approved=False,cache_admitted=False)
