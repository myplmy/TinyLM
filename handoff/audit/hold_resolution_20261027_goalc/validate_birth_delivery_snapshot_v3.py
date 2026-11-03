"""Reuse v2 while explicitly quarantining raw mechanical review rejections."""
from pathlib import Path
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from quarantine_rejected_birth_row_v1 import quarantine_rejected_row

frozen = AUDIT / 'validate_birth_delivery_snapshot_v2.py'
code = frozen.read_text(encoding='utf-8')
anchor = "exec(compile(code, str(frozen), 'exec'), globals())"
assert code.count(anchor) == 1
injection = '''anchor = "        guard.require(raw_row['original']['sha256'] == sources[ident]['original']['sha256'],"
assert code.count(anchor) == 1
code = code.replace(anchor, """        rejected = quarantine_rejected_row(raw_row, sources[ident], raw['errors'])
        if rejected is not None:
            counts[rejected['input_delivery']['status']] += 1
            failures.append(dict(id=ident, role=role, review=raw_row['review'],
                                 delivery=rejected['input_delivery'], error=rejected['raw_review_error']))
            gated.append(rejected)
            continue
""" + anchor)
anchor = "                  activation=pin(activation_path), config=config_pin, module=activation['module'],"
assert code.count(anchor) == 1
code = code.replace(anchor, anchor + chr(10) +
    "                  rejected_row_helper=pin(AUDIT / 'quarantine_rejected_birth_row_v1.py')," + chr(10) +
    "                  validator_reused_entry=pin(AUDIT / 'validate_birth_delivery_snapshot_v2.py'),")
'''
code = code.replace(anchor, injection + chr(10) + anchor)
exec(compile(code, str(frozen), 'exec'), globals())
