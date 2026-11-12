"""Reuse stage7 with explicit six-source rule supplements supplied by config."""
from pathlib import Path
import hashlib

path=Path(__file__).with_name('record_hold_stages_v7.py')
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='B0579B8BE6F67B658CE7C76FD0079827FC9EB1D3D5ABB70E4D7457AA15F929CA'
code=raw.decode('utf-8')
before="spec['cohort']=='remaining_rule30_independent_context_v1' and spec['expected_sources']==6"
after="re.fullmatch(r'remaining_rule[1-9][0-9]*_independent_context_v1',spec['cohort']) and spec['expected_sources']==6"
assert code.count(before)==1
code=code.replace(before,after)
exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
