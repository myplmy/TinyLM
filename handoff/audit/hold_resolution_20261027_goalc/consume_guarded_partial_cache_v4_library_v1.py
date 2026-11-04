"""Reuse the proven library consumer with adapter5; do not enter CLI aliases."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'consume_guarded_partial_cache_v3_library_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='F201D0C64C1FF22EF892F516DDB8C892AFC1744560D2427C592AACE55086D572'
code=frozen.read_text(encoding='utf-8')
before='import guarded_reviewed_cache_v4 as guarded'
assert code.count(before)==1;code=code.replace(before,'import guarded_reviewed_cache_v5 as guarded')
before='aliases=[guarded.previous.verify,guarded.previous.previous.verify,guarded.previous.first.verify]'
assert code.count(before)==1
code=code.replace(before,'aliases=[guarded.previous.verify,guarded.previous.previous.verify,guarded.previous.previous.previous.verify,guarded.first.verify]')
exec(compile(code,str(frozen),'exec'),dict(__name__=__name__,__file__=str(Path(__file__))))
