"""Bind the author's exact corrected review and archive its failed edit."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

directory=inv.BASE/'agents/historical_review/runtime_guard_counter_v1'
failed=directory/'review_001_v4.md'
corrected=directory/'review_001_v4_corrected.md'
binding=inv.cache.read(AUDIT/'AUTHOR_REVIEW_EXPLICIT_BINDINGS_V1.json')
binding['rows'].append(dict(role='historical_review',cohort='runtime_guard_counter_v1',batch=1,
    path=str(corrected.relative_to(ROOT)),sha256=inv.file_sha(corrected),root_approved=True,
    reason='작성자가실패v4와구별해명시한정확수정리뷰; 다른본문을버전으로선택하지않음'))
inv.write_json(AUDIT/'AUTHOR_REVIEW_EXPLICIT_BINDINGS_V2.json',binding)
auxiliary=inv.cache.read(AUDIT/'AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V2.json')
auxiliary['rows'].append(dict(path=str(failed.relative_to(ROOT)),sha256=inv.file_sha(failed),
    canonical_review=str(corrected.relative_to(ROOT)),canonical_review_sha256=inv.file_sha(corrected),
    root_approved=True,original_auxiliary_preserved=True,root_body_authorship=False,cache_admitted=0,
    disposition='FAILED_AUTHOR_REVIEW_EDIT_PRESERVED_NOT_DECISION_EVIDENCE',
    reason='작성자가sed편집실패로선언한원형리뷰이며정확corrected리뷰를별도로지정했다.'))
inv.write_json(AUDIT/'AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V3.json',auxiliary)
source=(AUDIT/'collect_supplemental_candidates_v59.py').read_text(encoding='utf-8')
for before,after in [
 ('supplemental_candidates_snapshot_v59.json','supplemental_candidates_snapshot_v60.json'),
 ('AUTHOR_REVIEW_EXPLICIT_BINDINGS_V1.json','AUTHOR_REVIEW_EXPLICIT_BINDINGS_V2.json'),
 ('AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V2.json','AUTHOR_AUXILIARY_REVIEW_DISPOSITIONS_V3.json'),
 ('def review_rank(path):', '''def review_rank(path):
    exact = [row for row in bindings if row["path"] == str(path.relative_to(ROOT))]
    if exact:
        inv.require(len(exact)==1,"one review repeats an explicit binding")
        return int(exact[0]["batch"]), False, 0'''),
]:
    assert source.count(before)==1,before
    source=source.replace(before,after,1)
with (AUDIT/'collect_supplemental_candidates_v60.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
plan=(AUDIT/'materialize_reviewed_selection_plan_v36.py').read_text(encoding='utf-8')
for before,after in [('reviewed_selection_plan_v36.json','reviewed_selection_plan_v37.json'),
                     ('supplemental_candidates_snapshot_v59.json','supplemental_candidates_snapshot_v60.json')]:
    assert plan.count(before)==1,before
    plan=plan.replace(before,after,1)
with (AUDIT/'materialize_reviewed_selection_plan_v37.py').open('x',encoding='utf-8') as stream:
    stream.write(plan)
preview=(AUDIT/'prepare_authored_root_selection_v10_preview6.py').read_text(encoding='utf-8')
for before,after in [('reviewed_selection_plan_v36.json','reviewed_selection_plan_v37.json'),
                     ('supplemental_candidates_snapshot_v59.json','supplemental_candidates_snapshot_v60.json')]:
    assert preview.count(before)==1,before
    preview=preview.replace(before,after,1)
with (AUDIT/'prepare_authored_root_selection_v10_preview6_bound.py').open('x',encoding='utf-8') as stream:
    stream.write(preview)
print('EXACT_AUTHOR_CORRECTED_REVIEW_BOUND_FAILED_EDIT_PRESERVED')
