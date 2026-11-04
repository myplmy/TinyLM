"""Reuse numeric context windows behind the current cumulative ID/SHA guard."""
from pathlib import Path
import hashlib
import sys
A=Path(__file__).resolve().parent
frozen=A/'read_literal_numeric_context_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='500E6B4E6CF88AC164C39F3F55328540B8BE077F07CFFDF7935C21CF2349AE48'
code=raw.decode()
for old,new in [('GUARDED_SOURCE_METADATA_CONTRACT_V1','GUARDED_SOURCE_METADATA_CONTRACT_V3'),('CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF','7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306')]:
    assert code.count(old)==1;code=code.replace(old,new,1)
anchor="        assert row['original']['sha256'] not in guard['restricted_hashes']"
assert code.count(anchor)==1
code=code.replace(anchor,anchor+"\n        assert row['body']['sha256'] not in guard['restricted_hashes']",1)
if '--full' in sys.argv:
    assert sys.argv.count('--full')==1
    sys.argv.remove('--full')
    anchor='        print(json.dumps(dict(id=row[\'id\'], role=row[\'role\'], original=row[\'original\'],'
    assert code.count(anchor)==1
    extra="        assert len(original)<=10000 and len(body)<=10000, 'request narrower explicit source ranges'\n        source_ranges=[[0,len(original)]];body_ranges=[[0,len(body)]]\n"
    code=code.replace(anchor,extra+anchor,1)
exec(compile(code,str(frozen),'exec'),{'__name__':'literal_numeric_context_guarded_v2','__file__':str(Path(__file__))})
