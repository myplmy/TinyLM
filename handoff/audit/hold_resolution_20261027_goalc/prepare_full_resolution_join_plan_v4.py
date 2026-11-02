"""Permit metadata-only protected drafts only when an exact authored choice replaces them."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'materialize_full_resolution_join_plan_v3.py').read_text(encoding='utf-8')
before="""                    inv.require(row['decision'] == 'PENDING' and row['id'] in contract['trusted_metadata'],
                                'restricted proposal cannot be inherited as an automatic body')"""
after="""                    inv.require(row['id'] in contract['trusted_metadata'], 'restricted source lacks metadata')
                    inv.require(row['decision'] == 'PENDING' or
                                (key in authored and authored[key]['selected']['decision'] in {'EDIT','EXCLUDE'}),
                                'restricted automatic body lacks an exact safe authored replacement')"""
assert source.count(before)==1
source=source.replace(before,after,1)
with (AUDIT/'materialize_full_resolution_join_plan_v4.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
print('PROTECTED_AUTOMATIC_KEEP_CANNOT_BYPASS_EXACT_SAFE_VIEW_REPLACEMENT')
