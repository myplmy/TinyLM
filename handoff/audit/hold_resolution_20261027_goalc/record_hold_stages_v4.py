"""Keep whole-stage arithmetic under current guard5; source bodies remain closed."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('record_hold_stages_v3.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='E1839619F7120E359B659F2FA9867D2869693CE52D1B1F536FF14CEDDCFD800E'
code=raw.decode()
for before,after in [
    ('active_guard_v4_preflight_v1','active_guard_v5_preflight_v1'),
    ('GUARDED_SOURCE_METADATA_CONTRACT_V4','GUARDED_SOURCE_METADATA_CONTRACT_V5'),
    ('59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',
     '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338')]:
    assert before in code;code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='guard5_stage_recorder',__file__=str(Path(__file__))))
