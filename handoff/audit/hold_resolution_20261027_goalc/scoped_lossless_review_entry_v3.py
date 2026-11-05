"""Pin the smaller long-document core and expose both exact input choices."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('scoped_lossless_review_entry_v2.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '72B5374D1099EFFEDF785B595D0711141441D6115E3D914EB387BA45BB9820BF'
code = raw.decode('utf-8')
old = 'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v2.py'
assert code.count(old) == 1
code = code.replace(old,'handoff/audit/hold_resolution_20261027_goalc/lossless_review_packet_v3.py')
old = '    info.update(accept_output_absolute='
assert code.count(old) == 1
code = code.replace(old,"    info.update(keep_output_absolute=str(root/context['original']['path']),accept_output_absolute=")
exec(compile(code,str(frozen),'exec'),globals())
