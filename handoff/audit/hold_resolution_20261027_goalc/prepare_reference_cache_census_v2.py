"""Keep the metadata-only reference census and fingerprint cache runtime8."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('prepare_reference_cache_census_v1.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '85C73FA7E9BBB431D3B5F4440677B060010514E7B0EBD89E217AA799BFCFAD86'
code = raw.decode('utf-8')
before = 'from guarded_reviewed_cache_v7 import ROOT, inv, current_pins, checked_contract'
assert code.count(before) == 1
code = code.replace(before, 'from guarded_reviewed_cache_v8 import ROOT, inv, current_pins, checked_contract')
exec(compile(code, str(frozen), 'exec'), dict(__name__='guard5_reference_census',
    __file__=str(Path(__file__))))
