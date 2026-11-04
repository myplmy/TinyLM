"""Process-local guard4 preflight and payload-open diagnostics for collectors."""
from pathlib import Path
from guarded_reviewed_cache_v6 import checked_contract, EXPECTED, ROOT
from exact_review_metadata_guard_v2 import install_open_observer

ATTEMPTS = None


def activate():
    global ATTEMPTS
    if ATTEMPTS is None:
        contract = checked_contract()
        # Include all parent aliases; the new historical ordinal is 267904.
        diagnostic = dict(contract, restricted_ids=sorted(set(contract['restricted_ids']) |
            set(contract['trusted_metadata'])))
        ATTEMPTS = install_open_observer(ROOT, diagnostic)
    return EXPECTED


def attempted_payload_opens():
    assert ATTEMPTS is not None, 'guard4 observer was not activated'
    return len(ATTEMPTS)


def assert_no_protected_opens():
    assert attempted_payload_opens() == 0, 'a protected payload open was attempted'
