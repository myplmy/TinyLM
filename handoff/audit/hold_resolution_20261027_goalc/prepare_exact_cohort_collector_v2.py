"""Keep a specifically adjudicated source-free explanation outside decisions."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=AUDIT/'collect_exact_cohort_reviews_v1.py'
target=AUDIT/'collect_exact_cohort_reviews_v2.py'
assert not target.exists()
text=source.read_text(encoding='utf-8')
before='    environment=dict(ROOT=ROOT,BASE=base,AUDIT=AUDIT,Path=Path,re=re,hashlib=hashlib,inv=inv,'
after='''    auxiliary_path=AUDIT/'EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V1.json'
    auxiliary_records=inv.cache.read(auxiliary_path)['rows']
    auxiliary_by_path={r['path']:r for r in auxiliary_records}
    inv.require(len(auxiliary_by_path)==len(auxiliary_records),'duplicate explicit auxiliary')
    for auxiliary in auxiliary_records:
        inv.require(auxiliary['root_approved'] is True and auxiliary['original_auxiliary_preserved'] is True,
                    'unapproved auxiliary explanation')
        inv.require(inv.file_sha(ROOT/auxiliary['path'])==auxiliary['sha256'],'auxiliary bytes changed')
        inv.require(inv.file_sha(ROOT/auxiliary['canonical_review'])==auxiliary['canonical_review_sha256'],
                    'canonical restored review changed')
    environment=dict(ROOT=ROOT,BASE=base,AUDIT=AUDIT,Path=Path,re=re,hashlib=hashlib,inv=inv,'''
assert text.count(before)==1
text=text.replace(before,after)
before='bindings=[],auxiliary_by_path={},retractions=[],auxiliary_review_history=[],'
assert text.count(before)==1
text=text.replace(before,'bindings=[],auxiliary_by_path=auxiliary_by_path,retractions=[],auxiliary_review_history=[],')
before='for pin_path in [manifest_path,contract_path,reused_path,Path(__file__)]:'
assert text.count(before)==1
text=text.replace(before,'for pin_path in [manifest_path,contract_path,reused_path,auxiliary_path,Path(__file__)]:')
before="for review in sorted(directory.glob('review*.md'),key=env['review_rank']):"
assert text.count(before)==1
text=text.replace(before,"for review in sorted([p for p in directory.glob('review*.md') if str(p.relative_to(ROOT)) not in auxiliary_by_path],key=env['review_rank']):")
before="review_history=histories,review_pins=env['review_pins'],sidecars=sidecars,"
assert text.count(before)==1
text=text.replace(before,"review_history=histories,review_pins=env['review_pins'],sidecars=sidecars,"+chr(10)+
    "        auxiliary_review_history=[dict(r,excluded_as_duplicate_decision=False,excluded_as_nondecision_auxiliary=True) for r in env['auxiliary_review_history']],")
with target.open('x',encoding='utf-8') as stream:stream.write(text)
print('정확 보조기록 등록을 반영한 수집기 V2 준비')
