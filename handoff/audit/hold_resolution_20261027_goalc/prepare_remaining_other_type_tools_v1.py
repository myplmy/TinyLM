"""Adapt the existing full census and native verifier to their exact complement."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
census=(AUDIT/'census_remaining_field_title_full_sources_v1.py').read_text(encoding='utf-8')
changes=[
    ('remaining_field_title_full_sources_v1','remaining_other_types_full_sources_v1'),
    ("if reason in r['previous_reasons']","if reason not in r['previous_reasons']"),
    ("assert len(rows)==source['pending_reasons_unique'][reason]==18237",
     "assert len(rows)==source['counts']['queued_unique']-source['pending_reasons_unique'][reason]==50162"),
    ("['ENTIRE_REMAINING_FIELD_OR_TITLE_TYPE']","['ENTIRE_REMAINING_OTHER_TYPES',*row['previous_reasons']]"),
    ('all_field_title_sources','all_other_type_sources'),
    ('ENTIRE_FIELD_TITLE_TYPE_PAGINATED_NOT_REVIEWED','ENTIRE_OTHER_TYPES_PAGINATED_NOT_REVIEWED'),
]
for before,after in changes:
    assert before in census,before
    census=census.replace(before,after)
census=census.replace('18237','50162').replace('36','98').replace('field/title','other-type')
assert '18237' not in census and 'len(pages)==98' in census
path=AUDIT/'census_remaining_other_types_full_sources_v1.py'
with path.open('x',encoding='utf-8') as stream:stream.write(census)
native=(AUDIT/'verify_remaining_field_title_native_v1.py').read_text(encoding='utf-8')
for before,after in [
    ('remaining_field_title_full_sources_v1','remaining_other_types_full_sources_v1'),
    ('remaining_field_title_native_proofs_v1','remaining_other_types_native_proofs_v1'),
    ("remaining=set(result['reasons']);remaining.discard('UNRESOLVED_FIELD_OR_TITLE')",
     "remaining=set(result['reasons'])"),
    ('fresh_native_full_field_title_type','fresh_native_full_other_types'),
    ('ENTIRE_FIELD_TITLE_FRESH_NATIVE_PREPARATION_NOT_REVIEW_OR_ADMISSION',
     'ENTIRE_OTHER_TYPES_FRESH_NATIVE_PREPARATION_NOT_REVIEW_OR_ADMISSION'),
]:
    assert before in native,before
    native=native.replace(before,after)
native=native.replace('18237','50162').replace('36','98')
assert '18237' not in native and 'len(reports)==98' in native
path=AUDIT/'verify_remaining_other_types_native_v1.py'
with path.open('x',encoding='utf-8') as stream:stream.write(native)
print('exact other-type census/native adapters saved; no source prose authored')
