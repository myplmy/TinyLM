"""Reuse the frozen roster join from roster3 plus exact ROOT12 additions."""
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'prepare_reviewed_partial_roster_v3.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='BFC90217A518F0CB805FAA8894B2E8844800CD7F3E260EAF94D6D14B5BC46D92'
selection=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'
assert hashlib.sha256(selection.read_bytes()).hexdigest().upper()=='C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'
code=frozen.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen roster anchor changed',before)
    code=code.replace(before,after)


once('import guarded_reviewed_cache_v4 as guarded','import guarded_reviewed_cache_v5 as guarded')
once("plan_path=inv.BASE/'resolution_join_plan_v4/complete.json'",
     "plan_path=inv.BASE/'roster_reviewed_partial_v3/complete.json'")
once("selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'",
     "selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'")
once("approval_path=AUDIT/'ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json'",
     "approval_path=AUDIT/'ROOT_REVIEWED_PARTIAL_ADMISSIONS_V4.json'")
once("roster_dir=inv.BASE/'roster_reviewed_partial_v3'","roster_dir=inv.BASE/'roster_reviewed_partial_v4'")
once("census_dir=inv.BASE/'guarded_partial_proposals_v3'","census_dir=inv.BASE/'guarded_partial_proposals_v4'")
once("adoptions_path=inv.BASE/'reviewed_partial_adoptions_v3.json'",
     "adoptions_path=inv.BASE/'reviewed_partial_adoptions_v4.json'")
once('plan,selection=map(inv.cache.read,[plan_path,selection_path])',
    "plan,selection=map(inv.cache.read,[plan_path,selection_path])"+chr(10)+
    "assert plan['remaining_hold']==110173 and plan['unique_counts']['HOLD']==70230"+chr(10)+
    "assert inv.file_sha(ROOT/plan['approval']['path'])==plan['approval']['sha256']"+chr(10)+
    "plan=dict(plan,occurrence_counts=plan['counts'],full_restricted_original_bodies_opened=False,"+
    "input_pins={plan['approval']['path']:plan['approval']['sha256']})")
once("assert selection['source_ids']==7857 and selection['unresolved_sources']==0",
     "assert selection['source_ids']==7980 and selection['unresolved_sources']==0")
once("assert len(authored)==7857 and all(r['root_approved'] for r in authored.values())",
     "assert len(authored)==selection['source_ids'] and all(r['root_approved'] for r in authored.values())")
once('cases=guarded.previous.hold_cases()','cases=guarded.previous.previous.hold_cases()')
once("assert unique['HOLD']==70230 and len(set(cases)&set(outcomes))==38",
     "assert unique['HOLD']==selection['expected_roster_HOLD_unique'] and len(set(cases)&set(outcomes))==38"+
     chr(10)+"assert positions['HOLD']==selection['expected_roster_HOLD_positions']")
once("paths=[plan_path,selection_path,AUDIT/'ROOT11_COMPLETED_COHORT_ADMISSION_SCOPE_V1.md',",
     "paths=[AUDIT/'prepare_reviewed_partial_roster_v3.py',plan_path,selection_path,AUDIT/'ROOT12_COUNTER_BATCH001_ADMISSION_SCOPE_V1.md',")
once("AUDIT/'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json'",
     "AUDIT/'ROOT12_COUNTER_BATCH001_CLOSURE_V1.json'")
once("AUDIT/'guarded_reviewed_cache_v4.py'","AUDIT/'guarded_reviewed_cache_v5.py'")
once("independent_birth_second_reading='NOT_COMPLETED'",
     "independent_counter_selected_body_review='COMPLETED_ONLY_FOR_SELECTED_BATCH'")
once('literal_ids=set(guarded.previous.reviewed.literal.load_registry())|guarded.previous.previous.exact.EXPECTED',
     'literal_ids=set(guarded.first.reviewed.literal.load_registry())|guarded.previous.previous.previous.exact.EXPECTED')
once('with guarded.previous.reviewed.reviewed_inputs():','with guarded.first.reviewed.reviewed_inputs():')
environment=dict(__name__='reviewed_roster_v4_actual_run',__file__=str(Path(__file__)))
exec(compile(code,str(frozen),'exec'),environment)
