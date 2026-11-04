"""Preserve the V1 binder, restore duplicate checks, retire one exact bad draft."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'collect_root12_counter_v1.py'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest().upper()
assert sha(frozen)=='1CB0CD7C44E3892119A0C15873ED81E641F85351CE789CFD81DCD6CE81837870'
history=AUDIT/'ROOT12_COUNTER_REVIEW013_HISTORY_DISPOSITION_V1.json'
assert sha(history)=='2B759D9864726B17031DFA8256612143DFB56245F8B4DC9FE3A1555F009A546D'
document=json.loads(history.read_bytes())
assert document['root_approved'] is True and len(document['rows'])==1 and len(document['retractions'])==5
for row in document['rows']:
    assert row['root_approved'] is True and row['original_auxiliary_preserved'] is True
    assert sha(ROOT/row['path'])==row['sha256']
    assert sha(ROOT/row['canonical_review'])==row['canonical_review_sha256']
for row in document['retractions']:assert sha(ROOT/row['review'])==row['review_sha256']
code=frozen.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen counter anchor changed',before)
    code=code.replace(before,after)


once('bindings=[],auxiliary_by_path={},retractions=[],auxiliary_review_history=[],review_pins=[],',
     "bindings=[],auxiliary_by_path={r['path']:r for r in HISTORY['rows']},retractions=HISTORY['retractions'],auxiliary_review_history=[],review_pins=[],")
once('for path in [manifest_path,guard_path,reused,Path(__file__),',
     'for path in [HISTORY_PATH,FROZEN_COLLECTOR,manifest_path,guard_path,reused,Path(__file__),')
guard_code="""invalid_latest={}
for role in manifest['assignments']:
    directory=inv.BASE/'agents'/role/GROUP
    reviews=[p for p in directory.glob('review*.md') if str(p.relative_to(ROOT)) not in env['auxiliary_by_path']]
    for review in sorted(reviews,key=env['review_rank']):
        payload=env['stable'](review);seen_ids=set()
        for entry in env['review_entries'](payload):
            key=env['ident'](entry['cells'][0])
            if key in seen_ids:invalid_latest[key]=str(review.relative_to(ROOT))
            seen_ids.add(key)
choices={};coverage={};seen=[]"""
once('choices={};coverage={};seen=[]',guard_code)
once("        assert source['role']==row['role']",
     "        assert source['role']==row['role']"+chr(10)+
     "        if invalid_latest.get(key)==row['review']['path']:"+chr(10)+
     "            raise ValueError('DUPLICATE_SOURCE_ROWS_IN_ONE_EXPLICIT_REVIEW')")
once('    reused_definitions=list(frozen.REUSED),reused_historical_top_level_executed=False,',
     "    retracted_review_history=env['retracted_history'],"+chr(10)+
     "    auxiliary_review_history=[dict(r,excluded_as_duplicate_decision=False,excluded_as_nondecision_auxiliary=True) for r in env['auxiliary_review_history']],"+chr(10)+
     "    exact_duplicate_row_check_restored_from_full_cohort_collector=True,"+chr(10)+
     '    reused_definitions=list(frozen.REUSED),reused_historical_top_level_executed=False,')
environment=dict(__name__='root12_counter_v2_actual_run',__file__=str(Path(__file__)),
    HISTORY=document,HISTORY_PATH=history,FROZEN_COLLECTOR=frozen)
exec(compile(code,str(frozen),'exec'),environment)
# The earlier ROOT12 inputs predate TASK013; audit their declarations separately.
prior=environment['inv'].cache.read(environment['inv'].BASE/
    'root12_independent_admission_counter_v1_snapshots/v3/complete.json')
assert not any(pin['path'].endswith('/review_013.md') and '/context_controls/' in pin['path']
               for pin in prior['review_pins'])
for pin in prior['review_pins']:
    payload=(ROOT/pin['path']).read_bytes();assert hashlib.sha256(payload).hexdigest().upper()==pin['sha256']
    ids=[environment['env']['ident'](entry['cells'][0])
         for entry in environment['env']['review_entries'](payload)]
    assert len(ids)==len(set(ids)),'a prior approved snapshot had duplicate source rows'
print('PRIOR_ROOT12_SNAPSHOT_DUPLICATE_ROWS_ZERO; PREMATURE_TASK013_ROWS_NOT_PREVIOUSLY_ADMITTED')
