"""Reuse the owned build/consumer lifecycle with the exact cache10 adapter."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('run_versioned_guarded_cache_v4.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='C301BD7D75FC08363FAD49ECDBC3209513531D550B7801887EEFC93DAC934F11'
text=raw.decode('utf-8')
anchor=chr(10)+"exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))"
assert text.count(anchor)==1
scope=dict(__name__='guard6_owned_cache_runner_transform',__file__=str(Path(__file__)))
exec(compile(text.split(anchor)[0],str(frozen),'exec'),scope)
code=scope['code']
for before,after in [
    ('from guarded_reviewed_cache_v7 import verify_configuration','from guarded_reviewed_cache_v10 import verify_configuration'),
    ('import guarded_reviewed_cache_v7 as guarded','import guarded_reviewed_cache_v10 as guarded')]:
    assert code.count(before)==1
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__=__name__,__file__=str(Path(__file__))))
