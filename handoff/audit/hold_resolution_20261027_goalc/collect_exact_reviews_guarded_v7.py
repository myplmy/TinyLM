"""Reuse collector6 parsing with cumulative guard4 and two exact opaque cases."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT/'collect_exact_reviews_guarded_v6.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'A16A029CE9AB7B4294B630690C0554ACF781652333EE86A55D4D0D583DB20F68'
code = raw.decode('utf-8')
before = "    receipt_path = AUDIT / 'ROOT_28876_METADATA_ONLY_NONADMISSION_V1.json'\n    receipt = inv.cache.read(receipt_path)\n    inv.require(receipt['guard']['sha256'] == GUARD, 'receipt names a different guard')\n    for label in ('author_review', 'sidecar', 'manifest'):\n        pin = receipt[label]\n        inv.require(inv.file_sha(ROOT / pin['path']) == pin['sha256'],\n                    'metadata-only evidence changed')\n    receipt = dict(receipt, receipt_pin=dict(path=str(receipt_path.relative_to(ROOT)),\n                                           sha256=inv.file_sha(receipt_path)))"
after = "    from exact_review_metadata_guard_v3 import load_receipts\n    receipt_path = AUDIT / 'ROOT_267902_METADATA_ONLY_NONADMISSION_V1.json'\n    receipt = load_receipts(contract)"
assert code.count(before) == 1
code = code.replace(before, after)
for before, after in [
    ('exact_review_metadata_guard_v2', 'exact_review_metadata_guard_v3'),
    ('GUARDED_SOURCE_METADATA_CONTRACT_V2.json', 'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'),
    ('E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B',
     '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D')]:
    assert before in code; code = code.replace(before, after)
before = "                         AUDIT/'exact_review_header_alias_v2.py', guard_path, receipt_path):"
after = "                         AUDIT/'exact_review_header_alias_v2.py', guard_path, receipt_path,\n                         AUDIT/'ROOT_28876_METADATA_ONLY_NONADMISSION_V1.json',\n                         AUDIT/'active_guard_v4_preflight_v1.py', frozen):"
assert code.count(before) == 1
code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__)), frozen=frozen))
