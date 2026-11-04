"""Close four numeric flags using exact source contexts; admit no documents."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
A=Path(__file__).resolve().parent
B=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins={}


def read_raw(path,expected=None):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
    if expected is not None:assert digest==expected,str(path)
    pins[str(path.relative_to(ROOT))]=digest
    return raw


def read(path,expected=None):
    return json.loads(read_raw(path,expected))


guard=read(A/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json','7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306')
diagnostic=read(A/'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json','09850C948D8F411052DC05CEA3363D6550DE205262773528A8E2AA662CE81977')
wanted={'expanded_train:1311311','expanded_train:1319376','expanded_train:47394','expanded_train:724641'}
old={}
for pin in diagnostic['shards']:
    for row in read(ROOT/pin['path'],pin['sha256']):
        if row['id'] in wanted:old[row['id']]=row
snapshot=read(B/'remaining_literal_full_counter_v1_snapshots/v22/complete.json','BE21795C431E3A7901F9C0836DF320000362C3B09C9319D873E997E6E8A43785')
assert not snapshot['errors']
current={}
for pin in snapshot['shards']:
    for row in read(ROOT/pin['path'],pin['sha256']):
        if row['id'] in wanted:current[row['id']]=row
assert set(old)==set(current)==wanted
prior_path=A/'LITERAL_NUMERIC_CONTEXT_BATCH003_ADJUDICATIONS_V1.json'
prior=read(prior_path)
assert (prior['total_closed_old_flags'],prior['remaining_literal_numeric_flags'],prior['remaining_literal_numeric_documents'])==(21,83,9)
prior_closed=set();seen=set()


def collect_prior(path):
    if path in seen:return
    seen.add(path);document=read(path)
    prior_closed.update(row['id'] for row in document.get('records',[]))
    for name,expected in document.get('input_pins',{}).items():
        dependency=ROOT/name
        if dependency.parent==A and 'ADJUDICATIONS' in dependency.name and dependency.suffix=='.json':
            read(dependency,expected);collect_prior(dependency)


collect_prior(prior_path)
assert wanted.isdisjoint(prior_closed)
records=[]
for key in sorted(wanted):
    before=old[key];now=current[key]
    assert len(before['numeric_atom_flags'])==1
    assert key not in guard['restricted_ids']
    assert before['body']['sha256']==now['clean_text_sha256']
    assert all(value not in guard['restricted_hashes'] for value in [before['original']['sha256'],before['body']['sha256'],now['clean_text_sha256']])
    texts=[]
    for pin in [before['original'],before['body']]:
        path=ROOT/pin['path'];assert path.resolve().is_relative_to(B)
        texts.append(read_raw(path,pin['sha256']).decode('utf-8'))
    original,body=texts
    read_raw(ROOT/now['review']['path'],now['review']['sha256'])
    flag=before['numeric_atom_flags'][0]
    lo,hi=flag['body_span'];assert body[lo:hi]==flag['body_token']
    if key.endswith(':1311311'):
        assert 'First, select the five majors with the highest median earnings.' in original
        assert 'In : top_5 = df.sort_values(by="Median", ascending=False).head()' in original
        assert 'Create a new DataFrame called top_5 to get the top five items of your list:' in body
        outcome='SOURCE_EXPLICIT_TOP_5_IDENTIFIER_AND_FIVE_ITEMS'
        reason='The prose repeats the exact top_5 identifier assigned in the adjacent original code and the original five-items condition; no head default or output was inferred.'
    elif key.endswith(':1319376'):
        assert 'Note – I have shown 2 concrete instances named ConcreteStrategy1 & ConcreteStrategy2 just for explanation.' in original
        assert 'ConcreteStrategy2are two subclasses of\nBaseStrategy.' in original
        assert 'ConcreteStrategy1 and ConcreteStrategy2 are two subclasses of\nBaseStrategy.' in body
        outcome='SOURCE_EXPLICIT_CONCRETE_STRATEGY_PAIR_IN_NOTE'
        reason='The source explicitly names both ConcreteStrategy1 and ConcreteStrategy2 in its explanatory note and says there are two subclasses; the flagged 1 is part of that existing identifier.'
    elif key.endswith(':47394'):
        assert '공분산 행렬을 단위 행렬 (identity matrix)에 ε을 곱한 (εΙ)' in original
        assert 'ε값을 추정해야 할 값으로 보지 않고 고정된 값으로 만들자.' in original
        assert '하나의 클러스터에만 1의 값을 가지고, 나머지 클러스터에서는 0의 값을 가지게 된다.' in original
        assert 'ε값은 추정 대상이 아닌 고정값으로 둔다.' in body
        assert 'ε값을 0에 근접시키면 데이터 오브젝트의 사후 확률은 가장 가까운 평균에 대응하는 한 클러스터에서 1로, 다른 클러스터들에서는 0으로 수렴한다.' in body
        outcome='SOURCE_EXPLICIT_ONE_ZERO_POSTERIOR_LIMIT_WITH_EPSILON_CONDITIONS'
        reason='The original prose explicitly contains the one/zero posterior claim, scaled-identity covariance and fixed-epsilon limit conditions. This closes a source-fidelity flag without reproving the theorem or restoring missing equations.'
    else:
        assert 'deselect_all() select_index(seg) print(seg) print(get_segment_score(seg)) do_global_wiggle_all(5)' in original
        assert 'this command wiggles the entire protein (similarly, we could have used do_global_wiggle_backbone(5) or do_global_wiggle_sidechain(5) instead).' in original
        assert 'The number inside the parentheses is called a parameter.' in original
        assert 'The call do_global_wiggle_all(5) wiggles the entire protein' in body
        outcome='SOURCE_EXPLICIT_WIGGLE_CALL_PARAMETER_FIVE'
        reason='The exact do_global_wiggle_all(5) call is in the preceding original loop, and the later source paragraph describes the same whole-protein action and parameter. No command was run or default parameter invented.'
    records.append(dict(id=key,original=before['original'],old_body=before['body'],current_body=dict(path=now['body'],sha256=now['clean_text_sha256']),current_review=now['review'],old_numeric_flags=before['numeric_atom_flags'],target_outcomes=[outcome],reason=reason,root_review_scope='FULL_SOURCE_AND_BODY_READ' if key.endswith(':1319376') else 'TARGET_SOURCE_PARAGRAPHS_CODE_AND_BODY_CONTEXTS_READ',source_context_review_completed=True,context_hints_are_not_proofs=True))
read_raw(Path(__file__))
result=dict(status='FOUR_SOURCE_CONTEXTS_FOUR_NUMERIC_TARGETS_CLOSED_NOT_ADMISSION',records=records,source_documents=4,flag_occurrences=4,source_supported_context_retained=4,additional_semantic_instruction_repairs=0,prior_closed_old_flags=21,total_closed_old_flags=25,remaining_literal_numeric_flags=79,remaining_literal_numeric_documents=5,generic_numeric_guard_changed=False,root_training_TXT_authored=0,root_or_cache_admissions=0,whole_source_math_or_fact_pass=False,model_or_example_code_executions=0,goal_complete=False,training_authorized=False,input_pins=pins)
raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8');assert len(raw)<20_000_000
with (A/'LITERAL_NUMERIC_CONTEXT_BATCH004_ADJUDICATIONS_V1.json').open('xb') as handle:handle.write(raw)
print(json.dumps({key:result[key] for key in ['status','total_closed_old_flags','remaining_literal_numeric_flags','remaining_literal_numeric_documents']}))
