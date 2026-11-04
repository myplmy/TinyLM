"""Keep the failed V1 run; distinguish nested hashes from top-level identity."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('prepare_opaque_hold_contract_v1.py')
expected = '9E9D5AAB5C3991DB0E743472E214B271CB9E3188338EE493F9ECB966301D1F9B'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == expected
code = raw.decode('utf-8')
before = "                    assert len(matches) <= 1\n                    if not matches or matches[0].decode('ascii').upper() not in hold_hashes:\n                        continue\n                    row = metadata.project_metadata(line)"
after = "                    if not any(value.decode('ascii').upper() in hold_hashes for value in matches):\n                        continue\n                    row = metadata.project_metadata(line)\n                    if row.get('original_text_sha256') not in hold_hashes:\n                        continue"
assert code.count(before) == 1
code = code.replace(before, after)
before = "    pins = config['input_pins']"
assert code.count(before) == 1
code = code.replace(before, before + "\n    pins = dict(pins, **{str(Path(__file__).with_name('prepare_opaque_hold_contract_v1.py').relative_to(ROOT)): '" + expected + "'})")
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
