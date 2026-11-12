"""Reuse guarded collector11 with the exact final-file/body prefix adapter."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
for name,expected in [
    ('collect_exact_reviews_guarded_v11.py','6BB3DA4D934B7C0755574FB57CD195306552EFF7E25CB95CB20FA18404CFFD74'),
    ('exact_review_output_cell_alias_v2.py','1F4010473EC47147600580AFA9BDECDC3677C6E6A53583C362F7BE35F929C198')]:
    path=AUDIT/name
    assert not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest().upper()==expected,name
frozen=AUDIT/'collect_exact_reviews_guarded_v11.py'
code=frozen.read_text(encoding='utf-8')
before='import exact_review_output_cell_alias_v1 as aliases'
assert code.count(before)==1
code=code.replace(before,'import exact_review_output_cell_alias_v2 as aliases')
before="AUDIT/'exact_review_output_cell_alias_v1.py',AUDIT/'exact_review_header_alias_v2.py',"
assert code.count(before)==1
code=code.replace(before,"AUDIT/'exact_review_output_cell_alias_v1.py',AUDIT/'exact_review_output_cell_alias_v2.py',"+
    "AUDIT/'REVIEW_CELL_ALIAS_TESTS_V3.log',AUDIT/'collect_exact_reviews_guarded_v11.py',AUDIT/'exact_review_header_alias_v2.py',")
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
