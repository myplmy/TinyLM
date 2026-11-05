"""Reuse core3/entry2 protocol with exact cumulative guard5 before payload IO."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('scoped_lossless_review_entry_v2.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '72B5374D1099EFFEDF785B595D0711141441D6115E3D914EB387BA45BB9820BF'
code = raw.decode('utf-8')
for before,after in [
    ('GUARDED_SOURCE_METADATA_CONTRACT_V4.json','GUARDED_SOURCE_METADATA_CONTRACT_V5.json'),
    ('59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',
     '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338'),
    ('handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v2.py',
     'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v3.py'),
    ('    info.update(accept_output_absolute=',
     "    info.update(keep_output_absolute=str(root/context['original']['path']),accept_output_absolute=")]:
    assert code.count(before) == 1,before
    code = code.replace(before,after)
exec(compile(code,str(frozen),'exec'),globals())
