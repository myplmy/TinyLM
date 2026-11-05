"""Keep roster2 join and its three prior safe derivatives under guard5."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('advance_reviewed_roster_v2.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='5A6E982307AB572D768BE05A3C730CD0238CB2C8484185BD575424122D5C86EC'
code=raw.decode()
for before,after in [
    ('active_guard_v4_preflight_v1','active_guard_v5_preflight_v1'),
    ('from guarded_reviewed_cache_v6 import checked_contract','from active_guard_v5_preflight_v1 import checked_contract'),
    ('GUARDED_SOURCE_METADATA_CONTRACT_V4.json','GUARDED_SOURCE_METADATA_CONTRACT_V5.json'),
    ('59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',
     '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338'),
    ('paths.extend([ADAPTER_V1_PATH,','paths.extend([ADAPTER_V2_PATH,ADAPTER_V1_PATH,')]:
    assert before in code;code=code.replace(before,after)
before='ADAPTER_V1_PATH=frozen,'
assert code.count(before)==1
code=code.replace(before,'ADAPTER_V1_PATH=frozen, ADAPTER_V2_PATH=ADAPTER_V2_PATH,')
exec(compile(code,str(frozen),'exec'),dict(__name__='guard5_versioned_roster',
    __file__=str(Path(__file__)),ADAPTER_V2_PATH=frozen))
