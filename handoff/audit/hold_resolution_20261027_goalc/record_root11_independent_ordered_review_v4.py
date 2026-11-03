"""Record nine actual reads and verify immutable-source code in the repaired body."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
prior_path=AUDIT/'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V3.json'
prior=inv.cache.read(prior_path)
source_path=AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
records={row['id']:row for row in inv.cache.read(source_path)['records']}
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows=list(prior['rows'])
findings={
 'expanded_train:1031233':('CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE','원문/선택문전부및diff를읽었다. 출생연도1962/1961은양쪽분리됐으나실제살아있는사람분류도삭제됐다. 서지의쪽빈항목과template행도남는다. 원래분류/모든채워진서지값을보존하도록원래legacy역할에위임했다.'),
 'expanded_train:1046131':('REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS','원문/선택문전부및diff를읽었다. 빈이름병기괄호제거와은/는문법연결만바뀌었고캐릭터명·작품·1991년/분류는그대로다. 원문외부사실의검증이아니다.'),
 'expanded_train:1052119':('CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE','원문/선택문전부및diff를읽었다. 실제姜志勇한자명이삭제됐고도입1952년만분리해분류1968년이잔류한다. 이름복원과양쪽상충연도동일분리를원래legacy역할에위임했다. 나머지출생월일/장소/경력/원문보도·학력은사실선택하지않는다.'),
}
for ident,(decision,finding) in findings.items():
    row=records[ident]
    assert ident not in contract['restricted_ids'] and row['original_text_sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT/row['original_comparison_source'])==row['original_text_sha256']
    assert inv.file_sha(ROOT/row['body'])==row['clean_text_sha256']
    rows.append({'id':ident,'original':{'path':row['original_comparison_source'],'sha256':row['original_text_sha256']},
        'body':{'path':row['body'],'sha256':row['clean_text_sha256']},'reviewer':'root',
        'full_original_and_selected_body_read':True,'full_diff_read':True,'observation_tool_chunk':'7c7b99',
        'finding':finding,'decision':decision,'source_fact_verification':False})
assert len({row['id'] for row in rows})==len(rows)==9
fixed=[]
for ident,role,name,chunk in [
 ('expanded_train:1021004','context_latin','reviewed_1021004_root11_v3.txt','c9f5b8'),
 ('expanded_train:1023734','historical_review','expanded_train_1023734_historical_review_20261103_v1.txt','3abd44')]:
    row=records[ident]
    assert ident not in contract['restricted_ids'] and row['original_text_sha256'] not in contract['restricted_hashes']
    path=inv.BASE/'agents'/role/'root11_ordered_additional_corrections_v1'/name
    original=(ROOT/row['original_comparison_source']).read_text(encoding='utf-8')
    text=path.read_text(encoding='utf-8')
    checks={}
    if ident.endswith(':1021004'):
        for label,start,end in [('c','#include <stdio.h>','return factor == number ? EXIT_FAILURE : EXIT_SUCCESS;'+chr(10)+'}'),
                                ('python','from itertools import count','            exit()'),
                                ('pseudocode','     x ← 2','         return d')]:
            assert original.count(start)==text.count(start)==1 and original.count(end)==text.count(end)==1
            before=original[original.index(start):original.index(end)+len(end)]
            after=text[text.index(start):text.index(end)+len(end)]
            assert before==after
            checks[label+'_original_bytes_preserved']=True
        assert '제곱근' not in text and '10403 = 101 · 103 인 예제' in text
        checks['unqualified_runtime_bound_removed']=True
    else:
        assert '(282km / h)' in original and '(282km / h)' in text
        block=text.split('로드스터 '+chr(10),1)[1].split('프로드라이브 V8 밴티지',1)[0]
        assert '최대 속도는 (282km / h)이다.' in block
        checks['same_speed_in_original_roadster_context']=True
    fixed.append({'id':ident,'body':{'path':str(path.relative_to(ROOT)),'sha256':inv.file_sha(path)},
        'full_corrected_body_root_read_tool_chunk':chunk,'full_old_to_new_diff_tool_chunk':'105ea2',
        'actual_specific_static_checks':checks,'decision':'SEMANTIC_CORRECTION_REVIEWED_NOT_ADOPTED',
        'in_new_root_selection':False,'in_cache3':False})
inv.write_json(AUDIT/'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V4.json',{
    'status':'NINE_ACTUAL_READS_THREE_REPAIRS_REVIEWED_TWO_NEW_REPAIRS_PENDING',
    'ordered_flag_sources':585,'actually_reviewed_sources':9,'remaining_unreviewed_flag_sources':576,
    'old_root11_acceptable_sources':4,'old_root11_sources_requiring_replacement':5,
    'corrected_semantic_reviewed_sources':3,'corrections_still_pending':2,'rows':rows,
    'corrected_1018113':prior['corrected_1018113'],'other_reviewed_corrections':fixed,
    'prior':{'path':str(prior_path.relative_to(ROOT)),'sha256':inv.file_sha(prior_path)},
    'input_pins':{str(path.relative_to(ROOT)):inv.file_sha(path) for path in (source_path,Path(__file__))},
    'sampling_error_rate_extrapolated':False,'original_code_executed':False,
    'old_cache_or_source_changed':False,'birth_independent_whole_second_reading':'NOT_COMPLETED',
    'whole_corpus_semantic_completion':False,'goal_complete':False,'training_authorized':False})
print('9 actual reviews; 3 replacement bodies reviewed; 2 repairs pending; 576 other flag reviews remain; code executed0')
