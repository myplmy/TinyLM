"""Reuse native interval decoding and ordered views for nine precise cases."""
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE,AUDIT = inv.BASE,Path(__file__).resolve().parent
OUT = BASE/'resume_guard_counter_20261102_v1'
inv.require(not OUT.exists(),'new immutable guard-counter namespace required')
started = time.monotonic()
audit_path = AUDIT/'fresh_author_body_literals_v2.json'
audit = inv.cache.read(audit_path)
role_ids = {
    'context_controls':['expanded_train:689736','expanded_train:1254536','expanded_train:852538','expanded_train:71604'],
    'context_latin':['expanded_train:8121','expanded_train:255342','expanded_train:1239923','expanded_train:1081376','expanded_train:1276826']
}
selected = {ident:role for role,ids in role_ids.items() for ident in ids}
body_map = {r['id']:r for r in audit['records'] if r['id'] in selected}
inv.require(len(selected)==len(body_map)==9,'all nine current actual bodies required')
restricted = {'expanded_train:14760','expanded_train:756966','expanded_train:15695',
    'expanded_train:1216576','expanded_train:1250821','expanded_train:20624','expanded_train:6030'}
inv.require(not set(selected)&restricted,'restricted parent cannot enter this packet')
draft_path = BASE/'draft_proposals_v26_delta_v1/complete.json'
draft = inv.cache.read(draft_path)
pins = draft['lineage']['source_code_sha256']
inv.require(len(pins)==66,'verified26 production scope differs')
for name,expected in pins.items():
    inv.require(inv.file_sha(ROOT/name)==expected,'frozen production source changed: '+name)
source_dir = draft_path.parent
inv.verify(source_dir/'unique',draft['unique_manifest'])
sources = {r['id']:r for r in inv.cache.rows(source_dir/'unique',draft['unique_manifest']) if r['id'] in selected}
inv.require(set(sources)==set(selected),'source IDs are not the verified26 canonical rows')
directory = OUT/'inputs'
directory.mkdir(parents=True)
evidence_path = AUDIT/'EVIDENCE_8121_JING_CITATION_V1.md'
evidence_copy = OUT/'EVIDENCE_8121_JING_CITATION_V1.md'
with evidence_copy.open('xb') as stream:
    stream.write(evidence_path.read_bytes())
rows,loads = [],Counter()
with ExitStack() as stack:
    scope = inv.cache.read(BASE/'scope.json')
    inv.require(all(spec['path'].startswith('data_cache/') and 'TinyDataset' not in spec['path'] for spec in scope['inputs']),
                'only previously authorized native cache sources are eligible')
    reader = inv.OriginalReader(scope,stack)
    for ident,role in selected.items():
        source,actual = sources[ident],body_map[ident]
        raw,complete,valid = reader.text(source)
        inv.require(complete and valid and inv.sha(raw)==actual['original_text_sha256'],
                    'fresh native original differs from current body review')
        inv.require(inv.file_sha(ROOT/actual['compare_source']['path'])==actual['compare_source']['sha256']
                    == inv.sha(raw),'the old exact original copy changed')
        payload = (ROOT/actual['body']).read_bytes()
        inv.require(inv.sha(payload.decode('utf-8'))==actual['clean_text_sha256'],'current saved body changed')
        pair = {}
        for kind,value in [('original',raw.encode('utf-8')),('candidate',payload)]:
            inv.require(0<len(value)<20_000_000,'ordered splitting is required')
            path = directory/(ident.replace(':','_')+'_'+kind+'.txt')
            with path.open('xb') as stream:
                stream.write(value)
            pair[kind] = dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
        diagnostic = {key:actual.get(key) for key in ['code_guard','unicode_guard','semantic_style_guard',
            'source_function_parentheses_losses','introduced_numeric_occurrences','introduced_editor_memo_occurrences']}
        metadata = {key:source[key] for key in ['id','source','split','source_ids','source_ids_sha256',
            'original_text_sha256','input_ids','occurrences','language_bucket']}
        rows.append(dict(metadata,**pair,role=role,candidate_decision='NEEDS_ROOT',
            candidate_reasons=['EXACT_ACTUAL_BODY_GUARD_DIAGNOSIS_REQUIRES_SOURCE_CONTEXT'],
            prior_actual_body=dict(path=actual['body'],sha256=actual['clean_text_sha256']),
            prior_review=actual.get('review'),prior_diagnostics=diagnostic,
            fresh_native_original=True,complete_eos=True,valid_utf8=True,root_approved=False))
        loads[role] += len(raw)
for role,ids in role_ids.items():
    destination = BASE/'agents'/role/OUT.name
    destination.mkdir(parents=True,exist_ok=False)
    instructions = [
        '# '+role+' / '+OUT.name,'',
        '역할은 지정 원문과 현재 후보의 전량 판독, 새 TXT/MD 정제와 정확 hold 근거뿐이다.',
        '허용 읽기는 이 START/TASK/READING_VIEWS, 지정 original/candidate와 순서뷰, 자신이 새로 저장한 txt/md다.',
        '8121만 지정 증거 사본을 추가로 읽을 수 있다. 이전 작성자 리뷰나 다른 역할 파일은 읽지 않는다.',
        '허용 쓰기는 이 폴더의 새 txt/md뿐이다. 기존 자기 파일도 덮기/삭제/이동/개명하지 않는다.',
        '코드/시험/통계/해시/Python/모델/GPU/Git/규약/공유원장/웹/외부/보호자료/다른 세션 접근은 금지한다.',
        'narrow nl/sed/tail/diff로 지정 텍스트를 읽고 새 텍스트 파일을 편집하는 행위만 허용한다.',
        '한 파일씩 도구 결과로 읽는다. 여러 파일을 cat으로 이어붙이면 마지막 LF가 없는 경계를 오독할 수 있다.',
        '원문/후보 모든 순서뷰와 실제 EOF 및 전체 diff를 끝까지 읽는다. 잘린 출력은 미판독이다.',
        '코드 표본/출력/호출 괄호와 숫자/단위/조건/부정/인용 주체를 보존한다. 틸드나 백틱만으로 모든 구간을 프로그램으로 간주하지 않는다.',
        '실제 식/매개변수/필드가 사라진 부분은 모형 지식으로 채우지 않고 직접 의존부를 원형 hold한다. 남은 본문이 독립적으로 이해되는지 확인한다.',
        '실제 소스 조각이 hold돼 호출 손실 신호가 남는다면 각 조각과 이유를 명시한다. 단지 경고를 없애려고 올바른 코드/인용/조건을 지우지 않는다.',
        '한 TASK를 마칠 때 표형 review_NNN.md를 저장한다. 열은 ID / 판정 / 실제 판독 범위 / 출력 / 구체 근거다.',
        '판정은 ACCEPT_CANDIDATE / REVISE_TEXT / KEEP_SOURCE / EXCLUDE / NEEDS_ROOT다. 출력 열은 최종 TXT 경로 하나만 쓴다.',
        '후보가 적절하면 정확 candidate 입력을 ACCEPT할 수 있다. 변경 시 전체 새 TXT와 hold를 저장하고 전체 diff와 새 EOF를 확인한다.',
        '근거가 모호하면 좁은 질문을 root에 보내고 다른 지정 TASK를 계속한다. 전체 캐시 채택이나 의미 PASS를 선언하지 않는다.'
    ]
    with (destination/'START_HERE.md').open('x',encoding='utf-8') as stream:
        stream.write(chr(10).join(instructions)+chr(10))
    for number,ident in enumerate(ids,1):
        row = next(r for r in rows if r['id']==ident)
        lines = ['# TASK_'+str(number).zfill(3),ident,'START_HERE와 READING_VIEWS를 따른다.',
            'original: '+str(ROOT/row['original']['path']),'original SHA256: '+row['original']['sha256'],
            'candidate: '+str(ROOT/row['candidate']['path']),'candidate SHA256: '+row['candidate']['sha256'],
            '원문 전체와 현재 저장 후보를 문맥으로 대조한다. 진단은 자동 오류 판정이 아니다.',
            '현재 진단: '+json.dumps(row['prior_diagnostics'],ensure_ascii=False)]
        if ident=='expanded_train:8121':
            lines += ['추가 허용 증거: '+str(evidence_copy),'증거 SHA256: '+inv.file_sha(evidence_copy)]
        with (destination/('TASK_'+str(number).zfill(3)+'.md')).open('x',encoding='utf-8') as stream:
            stream.write(chr(10).join(lines)+chr(10))
manifest = dict(status='NINE_FRESH_NATIVE_SOURCE_CURRENT_BODY_PAIRS_NOT_ADMISSION',rows=rows,
    assignments=role_ids,source_characters_by_role=dict(loads),source_code_pins=pins,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [audit_path,draft_path,BASE/'scope.json',evidence_path,Path(__file__)]},
    seconds=time.monotonic()-started,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.require(pins=={p:inv.file_sha(ROOT/p) for p in pins},'production sources changed')
inv.write_json(OUT/'manifest.json',manifest)
views = (AUDIT/'prepare_selected_literal_views_v3.py').read_text(encoding='utf-8')
views = views.replace('root_selected_literal_counter_v3',OUT.name)
with (AUDIT/'prepare_resume_guard_views_v1.py').open('x',encoding='utf-8') as stream:
    stream.write(views)
print(json.dumps(dict(rows=9,assignments={r:len(ids) for r,ids in role_ids.items()},
    source_characters_by_role=dict(loads),seconds=manifest['seconds']),ensure_ascii=False))
