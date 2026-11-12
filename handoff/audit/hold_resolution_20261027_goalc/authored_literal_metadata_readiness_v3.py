"""Apply the observed delimiter counterexample to every authored candidate."""
from pathlib import Path
import hashlib

path=Path(__file__).with_name('authored_literal_metadata_readiness_v2.py')
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='70EB1CF65343816A37BB50AB2FA9F4582937CE9762484EA1612D993A03CA3C27'
code=raw.decode('utf-8')
before='from close_remaining_heading_context_v1 import remaining_headings'
assert code.count(before)==1
code=code.replace(before,before+chr(10)+'from structural_delimiter_deferrals_v1 import deferrals as delimiter_deferrals')
before="failed+=deferrals(values[1])+policy.literal_holes(values[1])"
assert code.count(before)==1
code=code.replace(before,before+"+delimiter_deferrals(values[1])")
before="AUDIT/'close_remaining_heading_context_v1.py',AUDIT/'numeric_atom_integrity_v1.py']"
assert code.count(before)==1
code=code.replace(before,"AUDIT/'close_remaining_heading_context_v1.py',AUDIT/'numeric_atom_integrity_v1.py',"+
    "FROZEN_READINESS2,AUDIT/'structural_delimiter_deferrals_v1.py',AUDIT/'STRUCTURAL_DELIMITER_TESTS_V2.log']")
exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),FROZEN_READINESS2=path))
