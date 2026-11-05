"""Keep guard4 save logic and add only explicit owned code and active-log exclusions."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('prepare_versioned_checkpoint_v3.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'A68CBFFA5CFE0B362ECC0C3D80B0A297756845744F8BBD520DE3F994EA18BC47'
text = raw.decode('utf-8')
anchor = "exec(compile(raw, str(frozen), 'exec'), dict(__name__='current_guard4_owned_checkpoint',"
assert text.count(anchor) == 1
scope = dict(__name__='explicit_code_checkpoint_transform',__file__=str(Path(__file__)))
exec(compile(text.split(anchor)[0], str(frozen), 'exec'), scope)
code = scope['raw'].decode('utf-8')
before = 'for name in sorted(changed):'
assert code.count(before) == 2
code = code.replace(before, before + chr(10) + "    if name in c.get('active_audit_paths_excluded',[]):continue")
anchor = 'assert len(explicit)==len({r[\'path\'] for r in explicit})'
assert code.count(anchor) == 1
extra = """for name in c.get('additional_owned_code_paths',[]):
    assert name == 'scripts/p106b_hold_resolution_review_safeguards_v4.py'
    path=ROOT/name
    assert path.resolve().is_relative_to(ROOT/'scripts') and not path.is_symlink()
    assert 0 < path.stat().st_size < 20_000_000
    explicit.append(pin(path))
"""
code = code.replace(anchor, extra + anchor)
exec(compile(code, str(scope['frozen']), 'exec'), dict(__name__='guard4_checkpoint_with_owned_code',
    __file__=str(Path(__file__))))
