"""Reuse independent exact prefix/body checks and label the context batch."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('verify_authored_literal_selection_v1.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='544E1254ABE1ED0A206245049E97CE7D5D8B3FB0099CF44AAB2B12847B32862D'
code=raw.decode('utf-8')
for before,after in [
    ('PRIOR_PREFIX_AND_AUTHORED_LITERAL_BATCH_INDEPENDENTLY_VERIFIED',
     'PRIOR_PREFIX_AND_AUTHORED_CONTEXT_BATCH_INDEPENDENTLY_VERIFIED'),
    ('_AUTHORED_LITERAL_SELECTION_INDEPENDENT_VERIFIED_V1.json',
     '_AUTHORED_CONTEXT_SELECTION_INDEPENDENT_VERIFIED_V1.json')]:
    assert code.count(before)==1
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
