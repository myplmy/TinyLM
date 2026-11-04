"""Reuse unchanged diagnostics on the newly frozen 2720 field reviews."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'audit_field_bound_bodies_v1.py'
payload = frozen.read_bytes()
assert hashlib.sha256(payload).hexdigest().upper() == '017052EE5484CEF7AEF801612A4BC7838F6CCAE7867F8702C916D1943BCB7186'
code = payload.decode('utf-8')
changes = [
    ("VERSIONS = {1: 'v17', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v13', 7: 'v8', 8: 'v6'}",
     "VERSIONS = {1: 'v20', 2: 'v15', 3: 'v10', 4: 'v13', 5: 'v12', 6: 'v15', 7: 'v13', 8: 'v9', 9: 'v3'}"),
    ("target = BASE / 'field_bound_body_diagnostics_v1'", "target = BASE / 'field_bound_body_diagnostics_v3'"),
    ('assert reviewed_rows == 2224', 'assert reviewed_rows == 2720'),
    ("== 2220\nassert reviewed_rows - len(rows) == 4", "== 2714\nassert reviewed_rows - len(rows) == 6"),
    ('reviewed_bodyless_whole_holds=4', 'reviewed_bodyless_whole_holds=6'),
    ('ALL_2220_BOUND_FIELD_BODIES_CPU_READBACK_NOT_SEMANTIC_APPROVAL',
     'ALL_2714_BOUND_FIELD_BODIES_CPU_READBACK_NOT_SEMANTIC_APPROVAL'),
    ('FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json', 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V3.json'),
    ("for path in (source, collector, Path(__file__).resolve(), AUDIT / 'numeric_atom_integrity_v1.py',",
     "for path in (source, collector, Path(__file__).resolve(), AUDIT / 'audit_field_bound_bodies_v1.py', AUDIT / 'numeric_atom_integrity_v1.py',"),
]
for before, after in changes:
    assert code.count(before) == 1, before
    code = code.replace(before, after, 1)
exec(compile(code, str(frozen), 'exec'), globals())

