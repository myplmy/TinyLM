"""Recheck all predecessor rows and the exact ROOT13 delta independently."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'verify_reviewed_partial_roster_v4_v1.py'
expected='92B28B649DE749241C4660A26F741F0C3E32AF350B981507A8EA8BBB26B04BED'
code=frozen.read_text(encoding='utf-8')
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()==expected


def once(before,after):
    global code
    assert code.count(before)==1,('frozen independent roster verifier anchor changed',before)
    code=code.replace(before,after)


once("old_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'","old_path=inv.BASE/'roster_reviewed_partial_v4/complete.json'")
once("new_path=inv.BASE/'roster_reviewed_partial_v4/complete.json'","new_path=inv.BASE/'roster_reviewed_partial_v5/complete.json'")
once("selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'","selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V13.json'")
once("'C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'","'FDA9A45F054A0E1689322EBD69D16863E3C1F13FE2DE4FDF0CE9094C35D81AC9'")
once("prior=inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')","prior=inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json')")
code=code.replace('==123','==436').replace('==297416','==297103').replace('==70107','==69671')
code=code.replace('109931','109064').replace('109893','109026')
code=code.replace('ALL_ROSTER4_CANONICAL_ROWS_AND_EXACT_ROOT12_DELTA','ALL_ROSTER5_CANONICAL_ROWS_AND_EXACT_ROOT13_DELTA')
code=code.replace('ROOT12_ROSTER_V4_INDEPENDENT_VERIFIED_V1','ROOT13_ROSTER_V5_INDEPENDENT_VERIFIED_V1')
code=code.replace('changed_sources=123','changed_sources=436')
exec(compile(code,str(frozen),'exec'),dict(__name__='roster_v5_independent_actual_run',__file__=str(Path(__file__))))
