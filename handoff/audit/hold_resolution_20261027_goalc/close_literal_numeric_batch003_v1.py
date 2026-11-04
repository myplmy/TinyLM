"""Bind five manually reviewed numeric contexts and one author repair."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
B=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc';pins={}
sha=lambda raw:hashlib.sha256(raw).hexdigest().upper()
def read(path,expected=None):
    raw=path.read_bytes();digest=sha(raw)
    if expected is not None:assert digest==expected,str(path)
    pins[str(path.relative_to(ROOT))]=digest
    return json.loads(raw)
guard=read(A/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json','7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306')
d=read(A/'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json','09850C948D8F411052DC05CEA3363D6550DE205262773528A8E2AA662CE81977')
wanted={'expanded_train:220949','expanded_train:336682','expanded_train:1421842'}
old={}
for pin in d['shards']:
    for r in read(ROOT/pin['path'],pin['sha256']):
        if r['id'] in wanted:old[r['id']]=r
s=read(B/'remaining_literal_full_counter_v1_snapshots/v22/complete.json','BE21795C431E3A7901F9C0836DF320000362C3B09C9319D873E997E6E8A43785');assert not s['errors']
current={}
for pin in s['shards']:
    for r in read(ROOT/pin['path'],pin['sha256']):
        if r['id'] in wanted:current[r['id']]=r
assert set(old)==set(current)==wanted
assert sum(len(r['numeric_atom_flags']) for r in old.values())==5
expected={'expanded_train:220949':'8A46425E0E1D946BBBE749E75102C3226E75422A3DED009EC16ABB6A0153AC96','expanded_train:336682':'EF30124642BDD4CC6086278F630801F373FD624D4B8AA0456BC612468F3B8797','expanded_train:1421842':'D5136642DBF5CEE076961B1F1806889D317806020904461C018E0FF90E38E67B'}
records=[]
for key in sorted(wanted):
    before=old[key];now=current[key];assert now['clean_text_sha256']==expected[key]
    assert key not in guard['restricted_ids'] and all(v not in guard['restricted_hashes'] for v in [before['original']['sha256'],before['body']['sha256'],now['clean_text_sha256']])
    texts=[]
    for pin in [before['original'],before['body'],dict(path=now['body'],sha256=now['clean_text_sha256'])]:
        path=ROOT/pin['path'];assert path.resolve().is_relative_to(B) and not path.is_symlink()
        raw=path.read_bytes();assert sha(raw)==pin['sha256'];pins[pin['path']]=pin['sha256'];texts.append(raw.decode())
    original,prior,body=texts
    review_pin=now['review'];review_raw=(ROOT/review_pin['path']).read_bytes()
    assert sha(review_raw)==review_pin['sha256'];pins[review_pin['path']]=review_pin['sha256']
    if key.endswith(':220949'):
        assert body==prior
        assert '0x00; is a hexadecimal command caring 8-bit instruction.' in original
        assert 'This 8-bit instruction is written to each single pin of microcontroller.' in original
        assert 'If 1 is written it initializes the pin as input. can easily be written to the microcontroller port' in original
        assert 'The 8-bit instruction can easily be written to the microcontroller port' in body
        outcomes=['SOURCE_SUPPORTED_8_BIT_INSTRUCTION_ANTECEDENT']
        reason='The restored subject repeats the immediately preceding explicitly named 8-bit instruction; no bit width was invented.'
        source_review='FULL_SOURCE_AND_BODY_READ'
    elif key.endswith(':336682'):
        assert '2. ex. 2, p. 108.\nGiven that the domain of computation is 0 < x <=\n0 < z <= zmax ,' in original
        assert 'Exercise 2 gives the z-domain bound as 0 < z <= zmax.' in body
        marker='4. ex. 4, p. 108.\n';insert='Incorporate the 45 degree term for the collapsing spherical wave.\n'
        assert prior.count(marker)==1 and body==prior.replace(marker,marker+insert,1)
        assert insert.strip() in ' '.join(original.split())
        outcomes=['SOURCE_SUPPORTED_EXERCISE_2_HEADING_AND_Z_BOUND']
        reason='Exercise2 and its complete z bound are explicit in the source. The independently found complete Ex4 instruction was restored exactly; missing x limits and point-source coordinates were not invented.'
        source_review='FULL_SOURCE_OLD_BODY_NEW_BODY_AND_FULL_REPAIR_DIFF_READ'
    else:
        assert body==prior
        assert 'creates a window sized to a width of 700 pixels, and a height of 500:' in original
        assert 'size = (700, 500) screen = pygame.display.set_mode(size)' in original
        assert 'The 2 at the end specifies a line width of 2 pixels.' in original
        assert 'pygame.draw.rect(screen,BLACK,[20,20,250,100],2)' in original
        assert 'create a window 700 pixels wide and 500 pixels high.' in body
        assert 'a line width of 2 pixels makes the border 2 pixels thick.' in body
        outcomes=['SOURCE_SUPPORTED_WINDOW_WIDTH_700','SOURCE_SUPPORTED_WINDOW_HEIGHT_500','SOURCE_SUPPORTED_RECTANGLE_LINE_WIDTH_2']
        reason='Both original prose and actual code give the window dimensions and rectangle border width. Root read the target paragraphs/code and body contexts; no Pygame execution or whole-source semantic pass is claimed.'
        source_review='TARGET_SOURCE_PARAGRAPHS_CODE_AND_BODY_CONTEXTS_READ'
    assert len(outcomes)==len(before['numeric_atom_flags'])
    records.append(dict(id=key,original=before['original'],old_body=before['body'],current_body=dict(path=now['body'],sha256=now['clean_text_sha256']),current_review=now['review'],old_numeric_flags=before['numeric_atom_flags'],target_outcomes=outcomes,reason=reason,root_review_scope=source_review,source_context_review_completed=True,context_hints_are_not_proofs=True))
prior=read(A/'LITERAL_NUMERIC_CONTEXT_BATCH002_ADJUDICATIONS_V1.json')
assert prior['total_closed_old_flags']==16 and prior['remaining_literal_numeric_flags']==88 and prior['remaining_literal_numeric_documents']==12
assert wanted.isdisjoint({r['id'] for r in prior['records']})
document=dict(status='THREE_SOURCE_CONTEXTS_FIVE_NUMERIC_TARGETS_CLOSED_NOT_ADMISSION',records=records,source_documents=3,flag_occurrences=5,source_supported_context_retained=5,additional_semantic_instruction_repairs=1,prior_closed_old_flags=16,total_closed_old_flags=21,remaining_literal_numeric_flags=83,remaining_literal_numeric_documents=9,generic_numeric_guard_changed=False,root_training_TXT_authored=0,root_or_cache_admissions=0,whole_source_math_or_fact_pass=False,model_or_example_code_executions=0,goal_complete=False,training_authorized=False,input_pins=pins)
pins[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__).read_bytes())
out=A/'LITERAL_NUMERIC_CONTEXT_BATCH003_ADJUDICATIONS_V1.json';raw=(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode();assert len(raw)<20_000_000
with out.open('xb') as f:f.write(raw)
print(json.dumps({k:document[k] for k in ['status','flag_occurrences','additional_semantic_instruction_repairs','remaining_literal_numeric_flags','remaining_literal_numeric_documents']}))
