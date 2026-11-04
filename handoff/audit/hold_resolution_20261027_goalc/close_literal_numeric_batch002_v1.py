"""Link seven old numeric flags to exact contexts and the pinned cell repair."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc';pins={}
sha=lambda raw:hashlib.sha256(raw).hexdigest().upper()


def read(path):
    raw=path.read_bytes();pins[str(path.relative_to(ROOT))]=sha(raw);return json.loads(raw)


guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json';guard=read(guard_path)
assert pins[str(guard_path.relative_to(ROOT))]=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
diagnostic_path=AUDIT/'LITERAL_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json';d=read(diagnostic_path)
assert pins[str(diagnostic_path.relative_to(ROOT))]=='09850C948D8F411052DC05CEA3363D6550DE205262773528A8E2AA662CE81977'
wanted={'expanded_train:1156330','expanded_train:1188700','expanded_train:1357468','expanded_train:1410700'}
old={}
for item in d['shards']:
    records=read(ROOT/item['path']);assert pins[item['path']]==item['sha256']
    for row in records:
        if row['id'] in wanted:old[row['id']]=row
assert set(old)==wanted and sum(len(row['numeric_atom_flags']) for row in old.values())==7
snapshot_path=BASE/'remaining_literal_full_counter_v1_snapshots/v21/complete.json';snapshot=read(snapshot_path)
current={}
for item in snapshot['shards']:
    records=read(ROOT/item['path']);assert pins[item['path']]==item['sha256']
    for row in records:
        if row['id'] in wanted:current[row['id']]=row
assert set(current)==wanted
cell_path=AUDIT/'LITERAL_1357468_SAMPLE_CELL_FOLLOWUP_VERIFIED_V1.json';cell=read(cell_path)
assert pins[str(cell_path.relative_to(ROOT))]=='9E4E08B0CF740F061705150DC531B28D090E392D6EACDECA275BD5D7A6E9FFF6'
assert cell['one_cell_only_11_to_7'] and cell['other_four_review_rows_unchanged'] and cell['EOF_unchanged']
records=[]
for key in sorted(wanted):
    row=old[key];now=current[key]
    assert key not in guard['restricted_ids'] and all(value not in guard['restricted_hashes'] for value in
        [row['original']['sha256'],row['body']['sha256'],now['clean_text_sha256']])
    texts=[]
    for item in [row['original'],dict(path=now['body'],sha256=now['clean_text_sha256'])]:
        raw=(ROOT/item['path']).read_bytes();assert sha(raw)==item['sha256'];pins[item['path']]=item['sha256'];texts.append(raw.decode('utf-8'))
    source,body=texts
    if key.endswith(':1156330'):
        assert 'then by 2 because you’ve got two sides to the roof' in source
        assert 'multiplied by 2 to account for the two parts of the roof' in body
        outcomes=['SOURCE_SUPPORTED_TWO_ROOF_SIDES_MULTIPLIER']
        reason='The unmatched body 2 is explicitly present in the original roof-area explanation; no inferred multiplier.'
    elif key.endswith(':1188700'):
        assert 'if confidence > 0.8:' in source and 'confidence threshold of 0.8' in source
        assert 'Each confidence is compared with the 0.8 threshold' in body
        outcomes=['SOURCE_SUPPORTED_DETECTION_CONFIDENCE_THRESHOLD']
        reason='Both original code and prose give detection confidence 0.8. The earlier heuristic face-distance window is rejected as a proof.'
    elif key.endswith(':1357468'):
        assert now['clean_text_sha256']==cell['new_body']['sha256']=='C986349AC1EEEEA0DA977C1742BF74F588355DE9F56395DB391BA68852C1244F'
        assert '[ 2 4 214 4]' in source and '| | 2 | 4 | 214 | 4 |' in body
        assert 'avg / total 0.93 0.93 0.93 935' in source
        assert '| avg / total | 0.93 | 0.93 | 0.93 | 935 |' in body
        assert '(216+221+214+219)/(227+244+224+240)' in source
        assert '150.93048128342246' in source and 'Accuracy value: 0.93048128342246' in body
        outcomes=['SOURCE_SUPPORTED_ONE_CELL_11_TO_7_REPAIR','SOURCE_CONFUSION_MATRIX_COUNT_2',
            'SOURCE_CLASSIFICATION_REPORT_AVERAGE_0_POINT_93','SOURCE_LINE15_PLUS_ACCURACY_TOKEN_SEPARATION']
        reason='One sample cell had consumed the next display-line number. The matrix count, report average and accuracy are original reported values; no model or benchmark was executed.'
    else:
        assert 'data sizes(<1024 bytes)' in source and 'small data sizes(<1024 bytes)' in body
        assert 'Sun X4270 Lynx server' in source and 'Sun X4270 Lynx server' in body
        assert '128k chunks' in source and '128k chunks' in body
        outcomes=['SOURCE_CONDITIONED_HISTORICAL_COPY_SIZE_THRESHOLD_1024']
        reason='The copydd/Sun X4270 Nehalem conditions and 128k comparison remain. This is an original historical report, not a new performance measurement.'
    assert len(outcomes)==len(row['numeric_atom_flags'])
    records.append(dict(id=key,original=row['original'],old_body=row['body'],
        current_body=dict(path=now['body'],sha256=now['clean_text_sha256']),current_review=now['review'],
        old_numeric_flags=row['numeric_atom_flags'],target_outcomes=outcomes,reason=reason,
        source_context_root_review_completed=True,context_hints_are_not_proofs=True))
out=AUDIT/'LITERAL_NUMERIC_CONTEXT_BATCH002_ADJUDICATIONS_V1.json'
document=dict(status='FOUR_SOURCE_CONTEXTS_SEVEN_NUMERIC_TARGETS_CLOSED_NOT_ADMISSION',records=records,
    source_documents=4,flag_occurrences=7,source_supported_context_retained=6,source_supported_cell_repair=1,
    prior_batch001_flags=9,total_closed_old_flags=16,remaining_literal_numeric_documents=12,
    remaining_literal_numeric_flags=88,old_diagnostic_numeric_flags=104,
    generic_numeric_guard_changed=False,code_or_model_execution=0,root_training_TXT_authored=0,
    current_body_source_hints_not_programmatic_semantic_proofs=True,
    source_wide_math_or_fact_pass=False,root_or_cache_admissions=0,
    input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__).read_bytes())}),
    goal_complete=False,training_authorized=False)
with out.open('x',encoding='utf-8') as stream:
    json.dump(document,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps({k:document[k] for k in ['status','flag_occurrences','source_supported_context_retained',
    'source_supported_cell_repair','remaining_literal_numeric_documents','remaining_literal_numeric_flags']},ensure_ascii=False))
