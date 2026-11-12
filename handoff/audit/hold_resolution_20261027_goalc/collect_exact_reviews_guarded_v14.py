"""Reuse collector13 for the new exact rule31 supplement; keep field collection."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'collect_exact_reviews_guarded_v13.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='33EB796A20851FC628B6B545623BA4CE32DAC9BF2B81317E7B6337012909688B'
code=frozen.read_text(encoding='utf-8')
for before,after in [
    ('remaining_rule30_independent_context_v1','remaining_rule31_independent_context_v1'),
    ('RULE30_CONTEXT_LOSSLESS_SCOPE_V1.json','RULE31_CONTEXT_LOSSLESS_SCOPE_V1.json')]:
    assert code.count(before)==1
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
