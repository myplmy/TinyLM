"""Reuse every authored/readiness gate and add only proven empty-section boundaries."""
from pathlib import Path
import hashlib

FROZEN_READINESS2 = Path(__file__).with_name('authored_literal_metadata_readiness_v2.py')
raw = FROZEN_READINESS2.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '70EB1CF65343816A37BB50AB2FA9F4582937CE9762484EA1612D993A03CA3C27'
code = raw.decode('utf-8')
for before, after in [
    ('from close_remaining_heading_context_v1 import remaining_headings',
     'from close_remaining_heading_context_v1 import remaining_headings' + chr(10) +
     'from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals' + chr(10) +
     'from authored_empty_section_literal_v1 import preservation as empty_section_preservation' + chr(10) +
     'from selection_metadata_store_v1 import SelectionStore'),
    ("    profile=read(config['profile'])", "    selected=SelectionStore(AUDIT).read(ROOT/config['selection']['path'],config['selection']['sha256'])" + chr(10) +
     "    selected_hashes={row['original_text_sha256'] for row in selected['rows']}" + chr(10) +
     "    pins[config['selection']['path']]=config['selection']['sha256']" + chr(10) + "    profile=read(config['profile'])"),
    ("        if row['remaining_deferrals'] or row['remaining_headings']:",
     "        if row['original']['sha256'] in selected_hashes:" + chr(10) + '            continue' + chr(10) +
     "        if row['remaining_deferrals'] or row['remaining_headings']:"),
    ('proof=preservation(*values)', 'proof=empty_section_preservation(*values)'),
    ("failed+=deferrals(values[1])+policy.literal_holes(values[1])",
     "failed+=deferrals(values[1])+policy.literal_holes(values[1])+delimiter_deferrals(values[1])"),
    ("AUDIT/'close_remaining_heading_context_v1.py',AUDIT/'numeric_atom_integrity_v1.py']",
     "AUDIT/'close_remaining_heading_context_v1.py',AUDIT/'numeric_atom_integrity_v1.py',FROZEN_READINESS2," +
     "AUDIT/'structural_delimiter_deferrals_v1.py',AUDIT/'authored_empty_section_literal_v1.py'," +
     "AUDIT/'AUTHORED_EMPTY_SECTION_LITERAL_F3_F4_V1.md',AUDIT/'AUTHORED_EMPTY_SECTION_TESTS_V1.log']")]:
    assert code.count(before) == 1
    code = code.replace(before, after)
exec(compile(code, str(FROZEN_READINESS2), 'exec'), dict(__name__='__main__',
    __file__=str(Path(__file__)), FROZEN_READINESS2=FROZEN_READINESS2))
