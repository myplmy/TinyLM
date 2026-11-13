"""Reuse exact authored admission checks with an explicit context-proof label."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('admit_authored_literal_batch_v1.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='AED76E4E39EC00F97C9098EE860D0E1A3DCCA2DB5F10ACA022992D1DDBFEBA8C'
code=raw.decode('utf-8')
for before,after in [
    ('EXISTING_PRIMARY_FULL_READ_ALL_ROW_LITERAL_PROOFS_ROOT_STRATIFIED_CONTEXT',
     'EXISTING_PRIMARY_FULL_READ_ALL_ROW_VALUES_AND_EXACT_ROOT_CONTEXT_PROOFS'),
    ('ROOT_APPROVED_EXISTING_AUTHORED_LITERAL_ONLY_RESULT','ROOT_APPROVED_EXISTING_AUTHORED_PINNED_CONTEXT_RESULT'),
    ('ROOT_CLOSED_AUTHORED_LITERAL_BATCH_WITH_EXPLICIT_CONTEXT_DEFERRALS',
     'ROOT_CLOSED_AUTHORED_CONTEXT_BATCH_WITH_EXPLICIT_CONTEXT_DEFERRALS'),
    ('PRIOR_VERIFIED_SELECTION_UNCHANGED_PLUS_PINNED_AUTHORED_LITERAL_BATCH',
     'PRIOR_VERIFIED_SELECTION_UNCHANGED_PLUS_PINNED_AUTHORED_CONTEXT_BATCH')]:
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
