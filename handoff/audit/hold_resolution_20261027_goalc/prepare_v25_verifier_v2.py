"""Correct only the overwritten resolution-field projection; keep all checks."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'verify_v25_artifacts_v1.py').read_text(encoding='utf-8')
changes = [
    ('DRAFT_V25_EXECUTION_RECEIPT_V1.json', 'DRAFT_V25_EXECUTION_RECEIPT_V2.json'),
    ('decisions, seen = {}, set()', 'decisions, reasons_by_source, seen = {}, {}, set()'),
    ('    decisions[key] = decision', '    decisions[key] = decision' + chr(10)
     + '    reasons_by_source[key] = actual["reasons"]'),
    ('    inv.require(inherited == expected, "occurrence identity, interval, source or metadata changed")',
     '''    # The producer explicitly overwrites inventory.resolution=NOT_REVIEWED.
    # Every other inherited field, and the exact output schema, must match.
    inv.require(expected["resolution"] == "NOT_REVIEWED", "unexpected inventory resolution")
    expected_inherited = {key: value for key, value in expected.items() if key != "resolution"}
    inv.require(set(actual) == set(expected) | {"resolution_reasons"}, "occurrence output schema changed")
    inv.require(inherited == expected_inherited, "occurrence identity, interval, source or metadata changed")'''),
    ('    inv.require(key in decisions and decisions[key] == decision, "occurrence decision does not match its actual unique source")',
     '''    inv.require(key in decisions and decisions[key] == decision, "occurrence decision does not match its actual unique source")
    inv.require(actual["resolution_reasons"] == reasons_by_source[key], "occurrence reason differs from its actual unique source")'''),
    ('    root_adopted=0, remaining_draft_pending=occurrences["PENDING"], verified_partial_cache_remaining_hold=160219,',
     '''    prior_verifier_failure=dict(path=str((AUDIT / "verify_v25_artifacts_v1.log").relative_to(ROOT)),
        sha256=inv.file_sha(AUDIT / "verify_v25_artifacts_v1.log"),
        cause="VERIFIER_REMOVED_UPDATED_RESOLUTION_FROM_ACTUAL_BUT_NOT_FROM_EXPECTED_PROJECTION"),
    root_adopted=0, remaining_draft_pending=occurrences["PENDING"], verified_partial_cache_remaining_hold=160219,''')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
output = AUDIT / 'verify_v25_artifacts_v2.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared verifier2; all identity fields plus exact occurrence reason mapping remain mandatory.')
