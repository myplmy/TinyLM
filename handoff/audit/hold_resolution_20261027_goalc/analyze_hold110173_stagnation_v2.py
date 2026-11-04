"""Update the frozen diagnosis with separate first-review, adoption and cache stages."""
from pathlib import Path
import hashlib
import json
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
frozen=AUDIT/'analyze_hold110173_stagnation_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='C462277BDC5BF706789BEA0A8D27D15A8FB0A52476C16447B473F3DDC40DD9FB'
old=frozen.read_text(encoding='utf-8');anchor='prior = read('
assert old.count(anchor)==1
prefix=old.split(anchor)[0]
prefix=prefix.replace("VERSIONS = {1:'v20',2:'v16',3:'v14',4:'v14',5:'v12',6:'v15',7:'v15',8:'v13',9:'v7',10:'v1'}",
    "VERSIONS = {1:'v20',2:'v16',3:'v15',4:'v15',5:'v13',6:'v15',7:'v15',8:'v14',9:'v8',10:'v2'}")
prefix=prefix.replace('GUARDED_SOURCE_METADATA_CONTRACT_V2','GUARDED_SOURCE_METADATA_CONTRACT_V3')
prefix=prefix.replace('E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B',
    '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306')
env=dict(__name__='hold_stagnation_v2_metadata_only',__file__=str(Path(__file__)))
exec(compile(prefix,str(frozen),'exec'),env)
read,pins,reviewed=env['read'],env['pins'],env['reviewed']
prior=read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json');prior_ids={r['id'] for r in prior['rows']}
assert set(reviewed)&prior_ids=={'expanded_train:1046282'}
fresh={key:value for key,value in reviewed.items() if key not in prior_ids}
fresh_positions=sum(row['source']['occurrences'] for row in fresh.values())
assert len(fresh)==5136 and fresh_positions==9261
initial_unread_unique=70192;initial_hold_positions=110173;old_reviewed_HOLD=38
unread_unique=initial_unread_unique-len(fresh)
unread_positions=initial_hold_positions-old_reviewed_HOLD-fresh_positions
assert unread_unique==65056 and unread_positions==100874
cache=read(AUDIT/'CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1.json')
assert cache['current_hold_positions']==109931 and cache['resolved_positions']==242
root12=read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json');root13=read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V13.json')
assert root13['rows'][:len(root12['rows'])]==root12['rows']
root12_new=root12['rows'][len(prior['rows']):]
root13_new=root13['rows'][len(root12['rows']):]
assert len(root12_new)==123 and len(root13_new)==436
assert {row['id'] for row in root12_new+root13_new}<=set(fresh)
root_positions=sum(fresh[row['id']]['source']['occurrences'] for row in root12_new+root13_new)
assert root_positions==1109==242+867
counter=read(BASE/'root12_independent_admission_counter_v1_snapshots/v5/complete.json')
assert counter['records']==560 and not counter['errors']
cache_decomposition=dict(still_first_unreviewed=unread_positions,
    first_reviewed_but_not_in_verified_cache=fresh_positions-242,prior_reviewed_HOLD=old_reviewed_HOLD)
root_decomposition=dict(still_first_unreviewed=unread_positions,
    first_reviewed_but_not_in_ROOT13=fresh_positions-root_positions,prior_reviewed_HOLD=old_reviewed_HOLD)
assert sum(cache_decomposition.values())==109931
assert sum(root_decomposition.values())==root13['expected_roster_HOLD_positions']==109064
receipt=dict(status='STAGNATION_CAUSE_RECONCILED_AND_FIRST_CACHE_DELTA_ACTUALLY_VERIFIED',
    recorded_at=datetime.now(timezone.utc).isoformat(),
    first_review_freeze=env['coverage'],initial_unprocessed_unique=initial_unread_unique,
    fresh_first_review_unique=len(fresh),fresh_first_review_positions=fresh_positions,
    still_first_unreviewed_unique=unread_unique,still_first_unreviewed_positions=unread_positions,
    fresh_review_percent_of_initial_unique=100*len(fresh)/initial_unread_unique,
    first_review_bodyless_rows=sum(not row['record'].get('body') for row in fresh.values()),
    official_cache='cache_reviewed_partial_v4',previous_official_HOLD_positions=110173,
    official_verified_HOLD_positions=109931,actual_cache_reduction_positions=242,
    cache_new_unique_accepted_documents=123,additional_duplicate_positions_excluded=119,
    official_remaining_HOLD_decomposition=cache_decomposition,
    ROOT13_new_sources=436,ROOT13_new_positions=867,
    ROOT12_plus_ROOT13_new_sources=559,ROOT12_plus_ROOT13_new_positions=1109,
    ROOT13_expected_HOLD_positions=109064,ROOT13_remaining_decomposition=root_decomposition,
    ROOT13_cache_built=False,ROOT13_cache_verified=False,
    independent_second_review_rows=560,second_reviews_added_to_first_review_count=0,
    direct_cause='Root deferred the next exact selections, roster join and immutable cache while reviews and diagnostics accumulated. Reporting only the last verified cache concealed that stage difference.',
    why_work_cost_increased=[
        'Most residual positions remain genuinely first-unread; 5,136 fresh unique first reviews cover only about 7.32 percent of the original 70,192 unread unique sources.',
        'Full source, selected body and diff were repeatedly read, with long documents and missing formula/subject/condition boundaries requiring context decisions.',
        'Root serially mediated simple and difficult cases, and independent checks found actual lost conditions and a reordered shortcut table that needed correction.',
        'Closed reviews waited with individually unresolved numeric/code/order cases, rather than being integrated in independently closed batches.',
        'A full cache build and independent consumer cost about 32.86 and 13.95 minutes in this observed batch; these fixed costs are separate from per-source reading.'
    ],
    causal_contribution_percentages='NOT_ESTABLISHED',hardware_slowdown='NOT_ESTABLISHED',
    observation_does_not_establish_continuing_per_document_slowdown=True,
    corrections_executed=[
        '123 independently closed sources / 242 positions were joined, actually cached and independently verified.',
        'Another 436 independently closed sources / 867 positions were ROOT-approved separately from the one unresolved frozen review.',
        'Two existing Luna roles counter-read other primary authors while three continue first reviews; no additional agent was spawned.',
        'The partial collector opened only saved input views and denied unreviewed payload access; its frozen v5 bound 560 rows with zero errors.',
        'Simple empty syntax, LF and clear maintenance banners can be recorded and handled without repeated root permission; ambiguous semantic boundaries remain individual decisions.'
    ],
    actual_build_seconds=cache['actual_build_seconds'],actual_consumer_seconds=cache['actual_consumer_seconds'],
    report_denominators='Positions are original cache occurrences, unique sources are SHA-linked canonical documents, and counter reviews are not new first reviews.',
    known_limits=['CPU cache integrity is verified; most residual content is still unprocessed.',
        'Train/val exact text overlap is zero; global original-article leakage remains unverified without article IDs.',
        'The preservation proof refers to the frozen cache_v5 baseline, not every intermediate selected body.',
        'This is neither all-fact verification nor model-quality evidence or permission to resume training.'],
    raw_original_or_candidate_TXT_opens_in_this_report=0,
    goal_complete=False,training_authorized=False,
    input_pins=dict(pins,**{str(frozen.relative_to(ROOT)):hashlib.sha256(frozen.read_bytes()).hexdigest().upper(),
        str(Path(__file__).relative_to(ROOT)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}))
out=AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V2.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps({k:receipt[k] for k in ['status','official_verified_HOLD_positions','fresh_first_review_unique',
    'still_first_unreviewed_positions','ROOT13_new_sources','ROOT13_new_positions']},ensure_ascii=False))
