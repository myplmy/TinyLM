"""Resume the exact partial metadata archive without deleting or overwriting it."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
source=AUDIT/'prepare_exact_followup_checkpoint_v18.py'
assert hashlib.sha256(source.read_bytes()).hexdigest().upper()=='2579829447D33C73481E3617BE276D52404F00E7F4DFDA357B35C6CA67ABB20E'
code=source.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen V18 recovery anchor changed',before)
    code=code.replace(before,after)


once("archive=AUDIT/'exact_followup_progress_archive_v18';assert not archive.exists()",
    "archive=AUDIT/'exact_followup_progress_archive_v18'"+chr(10)+
    "assert archive.is_dir() and not archive.is_symlink()"+chr(10)+
    "assert not (AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V18.json').exists()")
once("if choice['cohort']!=group:continue","if choice.get('cohort')!=group:continue")
anchor="exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive_source),'exec'),globals())"
replacement=anchor+chr(10)+"""
strict_new_copy=copy
def copy(source,target):
    if target.exists():
        assert target.resolve().is_relative_to(AUDIT) and not target.is_symlink()
        payload=source.read_bytes()
        assert len(payload)<20_000_000 and target.read_bytes()==payload
        return dict(source=pin(source),archive=pin(target),exact_partial_copy_reused=True)
    return strict_new_copy(source,target)
"""
once(anchor,replacement)
exec(compile(code,str(source),'exec'),dict(__name__='exact_v18_partial_metadata_recovery',__file__=str(Path(__file__))))
