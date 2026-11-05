"""Keep owned worker lifecycle and use the exact reference-census adapter."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('run_versioned_guarded_cache_v3.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '79E2D0D66E0035ECA2F6F30A868A60C828D3E4B495980533BFB048815FE4F170'
text = raw.decode('utf-8')
anchor = "exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))"
assert text.count(anchor) == 1
scope = dict(__name__='reference_census_runner_transform', __file__=str(Path(__file__)))
exec(compile(text.split(anchor)[0], str(frozen), 'exec'), scope)
code = scope['code']
for old, new in [
    ('from opaque_cache_census_support_v1 import verify_configuration',
     'from guarded_reviewed_cache_v7 import verify_configuration'),
    ('import guarded_reviewed_cache_v6 as guarded', 'import guarded_reviewed_cache_v7 as guarded')]:
    assert code.count(old) == 1
    code = code.replace(old, new)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
