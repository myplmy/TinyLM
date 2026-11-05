"""Keep exact opaque join; distinguish top-level identity from nested provenance."""
from pathlib import Path
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from opaque_parent_projection_v1 import matching_parent_metadata

frozen = AUDIT/'prepare_opaque_hold_contract_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '9E9D5AAB5C3991DB0E743472E214B271CB9E3188338EE493F9ECB966301D1F9B'
code = raw.decode('utf-8')
before = """                    matches = metadata.SOURCE_SHA.findall(line)
                    assert len(matches) <= 1
                    if not matches or matches[0].decode('ascii').upper() not in hold_hashes:
                        continue
                    row = metadata.project_metadata(line)
"""
after = """                    row = MATCHING_PARENT_METADATA(line, hold_hashes)
                    if row is None:
                        continue
"""
assert code.count(before) == 1
code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__='__main__',
    __file__=str(Path(__file__)), MATCHING_PARENT_METADATA=matching_parent_metadata))
