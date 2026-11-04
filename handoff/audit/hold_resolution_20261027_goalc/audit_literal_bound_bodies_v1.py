"""Reuse byte-pinned diagnostics on the completed literal snapshot v20."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'audit_field_bound_bodies_v1.py'
payload = frozen.read_bytes()
assert hashlib.sha256(payload).hexdigest().upper() == '017052EE5484CEF7AEF801612A4BC7838F6CCAE7867F8702C916D1943BCB7186'
code = payload.decode('utf-8')
changes = [
    ("VERSIONS = {1: 'v17', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v13', 7: 'v8', 8: 'v6'}",
     "VERSIONS = {'remaining_literal_full_counter_v1': 'v20'}"),
    ("sources = [(f'remaining_field_title_page_{page:03}_counter_v1', version) for page, version in VERSIONS.items()]",
     "sources = list(VERSIONS.items())"),
    ("target = BASE / 'field_bound_body_diagnostics_v1'", "target = BASE / 'literal_bound_body_diagnostics_v1'"),
    ('assert reviewed_rows == 2224', 'assert reviewed_rows == 1793'),
    ("== 2220\nassert reviewed_rows - len(rows) == 4", "== 1783\nassert reviewed_rows - len(rows) == 10"),
    ('reviewed_bodyless_whole_holds=4', 'reviewed_bodyless_whole_holds=10'),
    ('ALL_2220_BOUND_FIELD_BODIES_CPU_READBACK_NOT_SEMANTIC_APPROVAL',
     'ALL_1783_BOUND_LITERAL_BODIES_CPU_READBACK_NOT_SEMANTIC_APPROVAL'),
    ('FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json', 'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'),
    ('FIELD_BODY_DIAGNOSTICS_REUSE_IMPACT_V1.md', 'LITERAL_BODY_DIAGNOSTICS_REUSE_SCOPE_V1.md'),
    ("for path in (source, collector, Path(__file__).resolve(), AUDIT / 'numeric_atom_integrity_v1.py',",
     "for path in (source, collector, Path(__file__).resolve(), AUDIT / 'audit_field_bound_bodies_v1.py', AUDIT / 'numeric_atom_integrity_v1.py',"),
]
for before, after in changes:
    assert code.count(before) == 1, before
    code = code.replace(before, after, 1)
exec(compile(code, str(frozen), 'exec'), globals())
