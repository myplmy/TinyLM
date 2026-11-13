"""Reuse all row guards; add geography boundaries and test token-join profiles."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('authored_literal_metadata_readiness_v4.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='6FAAA7377FEDFF8AC96D58C7E72D3AB9F66DF6AEB503A80B340CD7E49504EB16'
text=raw.decode('utf-8')
anchor='exec(compile(code, str(FROZEN_READINESS2),'
assert text.count(anchor)==1
scope=dict(__name__='authored_geography_readiness_transform',__file__=str(Path(__file__)))
exec(compile(text.split(anchor)[0],str(frozen),'exec'),scope)
code=scope['code']
for before,after in [
    ('from authored_empty_section_literal_v1 import preservation as empty_section_preservation',
     'from authored_empty_section_literal_v2 import preservation as empty_section_preservation'),
    ("'WORD_ATOMS_IDENTICAL_ONLY_OTHER_CHARACTERS_DIFFER'}:",
     "'WORD_ATOMS_IDENTICAL_ONLY_OTHER_CHARACTERS_DIFFER','ADDED_OR_REPLACED_SOURCE_WORDS',"+
     "'DELETIONS_WITH_ONLY_PARTICLE_CHANGES'}:"),
    ("AUDIT/'AUTHORED_EMPTY_SECTION_LITERAL_F3_F4_V1.md',AUDIT/'AUTHORED_EMPTY_SECTION_TESTS_V1.log']",
     "AUDIT/'AUTHORED_EMPTY_SECTION_LITERAL_F3_F4_V1.md',AUDIT/'AUTHORED_EMPTY_SECTION_TESTS_V1.log',"+
     "AUDIT/'authored_empty_section_literal_v2.py',AUDIT/'AUTHORED_EMPTY_GEOGRAPHY_BOUNDARY_F3_F4_V1.md',"+
     "AUDIT/'AUTHORED_EMPTY_GEOGRAPHY_BOUNDARY_TESTS_V1.log',"+
     "AUDIT/'authored_literal_metadata_readiness_v4.py']")]:
    assert code.count(before)==1,before
    code=code.replace(before,after)
exec(compile(code,str(scope['FROZEN_READINESS2']),'exec'),dict(__name__='__main__',
    __file__=str(Path(__file__)),FROZEN_READINESS2=scope['FROZEN_READINESS2']))
