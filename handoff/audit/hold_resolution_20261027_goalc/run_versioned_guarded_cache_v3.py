"""Reuse owned-worker lifecycle with exact configurable census and early pin checks."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('run_versioned_guarded_cache_v2.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '06242A5E79B715511B28B995F123D700BDD7D046B80192B71530999051AF0CFA'
code = raw.decode('utf-8')
before = "proposal_name=f'guarded_partial_proposals_v{roster}')"
after = "proposal_name=c.get('proposal_name', f'guarded_partial_proposals_v{roster}'))"
assert code.count(before) == 1; code = code.replace(before, after)
before = '    return path, document'
after = "    sys.path.insert(0, str(AUDIT))\n    from opaque_cache_census_support_v1 import verify_configuration\n    verify_configuration(document)\n" + before
assert code.count(before) == 1; code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
