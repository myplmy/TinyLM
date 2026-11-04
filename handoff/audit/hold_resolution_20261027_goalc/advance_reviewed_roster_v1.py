"""Apply the frozen whole-roster join to one exact versioned admission config."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
c=json.loads(config_path.read_bytes());old_version,new_version=c['prior_roster'],c['next_roster']
assert isinstance(new_version,int) and new_version==old_version+1 and new_version>=6
frozen=AUDIT/'prepare_reviewed_partial_roster_v3.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='BFC90217A518F0CB805FAA8894B2E8844800CD7F3E260EAF94D6D14B5BC46D92'
selection_path=AUDIT/f"ROOT_AUTHORED_SELECTIONS_V{c['next_selection']}.json"
assert hashlib.sha256(selection_path.read_bytes()).hexdigest().upper()==c['selection_sha256']
selection=json.loads(selection_path.read_bytes());assert selection['source_ids']==len(selection['rows'])
proof_path=AUDIT/c['prior_roster_proof'];proof=json.loads(proof_path.read_bytes())
assert hashlib.sha256(proof_path.read_bytes()).hexdigest().upper()==c['prior_roster_proof_sha256']
old_path=ROOT/f'data_cache/p106b_hold_resolution_v1_20261027_goalc/roster_reviewed_partial_v{old_version}/complete.json'
assert hashlib.sha256(old_path.read_bytes()).hexdigest().upper()==c['prior_roster_sha256']
assert proof['input_pins'][str(old_path.relative_to(ROOT))]==c['prior_roster_sha256']
code=frozen.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen roster anchor changed',before)
    code=code.replace(before,after)


once('import guarded_reviewed_cache_v4 as guarded','import guarded_reviewed_cache_v5 as guarded')
once("plan_path=inv.BASE/'resolution_join_plan_v4/complete.json'",f"plan_path=inv.BASE/'roster_reviewed_partial_v{old_version}/complete.json'")
once("selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'",f"selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V{c['next_selection']}.json'")
for prefix in ['ROOT_REVIEWED_PARTIAL_ADMISSIONS_V','roster_reviewed_partial_v','guarded_partial_proposals_v','reviewed_partial_adoptions_v']:
    before=prefix+'3';after=prefix+str(new_version)
    assert before in code;code=code.replace(before,after)
once('plan,selection=map(inv.cache.read,[plan_path,selection_path])',
    'plan,selection=map(inv.cache.read,[plan_path,selection_path])'+chr(10)+
    f"assert inv.file_sha(plan_path)=={c['prior_roster_sha256']!r}"+chr(10)+
    f"assert plan['remaining_hold']=={c['prior_HOLD_positions']} and plan['unique_counts']['HOLD']=={c['prior_HOLD_unique']}"+chr(10)+
    "assert inv.file_sha(ROOT/plan['approval']['path'])==plan['approval']['sha256']"+chr(10)+
    "plan=dict(plan,occurrence_counts=plan['counts'],full_restricted_original_bodies_opened=False,"+
    "input_pins={plan['approval']['path']:plan['approval']['sha256']})")
once("assert selection['source_ids']==7857 and selection['unresolved_sources']==0",f"assert selection['source_ids']=={selection['source_ids']} and selection['unresolved_sources']==0")
once("assert len(authored)==7857 and all(r['root_approved'] for r in authored.values())","assert len(authored)==selection['source_ids'] and all(r['root_approved'] for r in authored.values())")
once('cases=guarded.previous.hold_cases()','cases=guarded.previous.previous.hold_cases()')
once("assert unique['HOLD']==70230 and len(set(cases)&set(outcomes))==38",
    "assert unique['HOLD']==selection['expected_roster_HOLD_unique'] and len(set(cases)&set(outcomes))==38"+chr(10)+
    "assert positions['HOLD']==selection['expected_roster_HOLD_positions']")
once("paths=[plan_path,selection_path,AUDIT/'ROOT11_COMPLETED_COHORT_ADMISSION_SCOPE_V1.md',",
    f"paths=[CONFIG_PATH,FROZEN_PATH,PRIOR_PROOF_PATH,plan_path,selection_path,AUDIT/{c['scope_stem']+'.md'!r},")
once("AUDIT/'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json'",f"AUDIT/{c['closure_stem']+'.json'!r}")
once("AUDIT/'guarded_reviewed_cache_v4.py'","AUDIT/'guarded_reviewed_cache_v5.py'")
once("independent_birth_second_reading='NOT_COMPLETED'",
    "independent_counter_review='COUNTER_SUBSET_ONLY',additional_root_context_sources=selection.get('additional_root_independent_context_sources',0)")
once('literal_ids=set(guarded.previous.reviewed.literal.load_registry())|guarded.previous.previous.exact.EXPECTED',
    'literal_ids=set(guarded.first.reviewed.literal.load_registry())|guarded.previous.previous.previous.exact.EXPECTED')
once('with guarded.previous.reviewed.reviewed_inputs():','with guarded.first.reviewed.reviewed_inputs():')
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_versioned_roster_join',__file__=str(Path(__file__)),
    CONFIG_PATH=config_path,FROZEN_PATH=frozen,PRIOR_PROOF_PATH=proof_path))
