"""Route existing exact candidates to a different existing reviewer role."""
from collections import Counter
from pathlib import Path
import ast
import difflib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE=inv.BASE
GROUP='root12_independent_admission_counter_v1'
OUT=BASE/GROUP
assert not OUT.exists()
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=inv.cache.read(guard_path)
preflight_path=BASE/'root12_guard_clear_preflight_v1/complete.json'
preflight=inv.cache.read(preflight_path)
assert inv.file_sha(AUDIT/'ROOT12_GUARD_CLEAR_PREFLIGHT_V1.json')=='AD2E78F3B2DC94CC0EAB852CD3C5CFB630B12362BC6FBC45DAD33517021F7338'
records_path=ROOT/preflight['records']['path']
assert inv.file_sha(records_path)==preflight['records']['sha256']
candidates=inv.cache.read(records_path)
deferred={f'expanded_train:{number}' for number in [19365,48589,59573,140961]}
assert len(candidates)==3692 and len({row['id'] for row in candidates})==3692
candidates=[row for row in candidates if row['id'] not in deferred]
assert len(candidates)==3688
roles=['context_controls','context_latin']
priorities={'context_controls':['expanded_train:'+str(n) for n in [56606,1060968,516640,1166147]],
            'context_latin':['expanded_train:1065478']}
forced={key:role for role,ids in priorities.items() for key in ids}
assigned={role:[] for role in roles}
costs=Counter()
prepared=[]
for row in candidates:
    assert row['id'] not in guard['restricted_ids']
    assert all(row[label]['sha256'] not in guard['restricted_hashes']
               for label in ('original','candidate','body'))
    values={}
    for label,key in [('original','original'),('candidate','body')]:
        pin=row[key];path=ROOT/pin['path']
        assert path.resolve().is_relative_to(BASE) and not path.is_symlink()
        assert inv.file_sha(path)==pin['sha256']
        values[label]=path.read_text(encoding='utf-8')
    prepared.append(dict(row=row,values=values,cost=sum(len(v) for v in values.values())))
for item in sorted(prepared,key=lambda v:(-v['cost'],v['row']['id'])):
    row=item['row'];available=[role for role in roles if role!=row['role']]
    reviewer=forced.get(row['id']) or min(available,key=lambda role:(costs[role],len(assigned[role]),role))
    assert reviewer in available
    item['reviewer']=reviewer;assigned[reviewer].append(row['id']);costs[reviewer]+=item['cost']
OUT.mkdir()
(OUT/'reading_packets_v1').mkdir()
frozen=AUDIT/'prepare_remaining_birth_readers_v1.py'
assert inv.file_sha(frozen)=='E313C04D320FF4364342DD561D543ACE85CA02863FCD44B9D5B259D218481D1A'
tree=ast.parse(frozen.read_text(encoding='utf-8'))
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='save']
assert len(functions)==1 and not functions[0].decorator_list
environment=dict(ROOT=ROOT,inv=inv)
exec(compile(ast.Module(body=functions,type_ignores=[]),str(frozen),'exec'),environment)
save=environment['save']
rows=[];by_id={};identity=[]
for item in prepared:
    before=item['row'];key=before['id'];values=item['values'];stem=key.replace(':','_')
    same=values['original'].encode('utf-8')==values['candidate'].encode('utf-8')
    assert not same or before['original']['sha256']==before['body']['sha256']
    delta=''.join(difflib.unified_diff(values['original'].splitlines(keepends=True),
        values['candidate'].splitlines(keepends=True),fromfile='original',tofile='prior_selected_body'))
    candidate_text=values['candidate'] if not same else (
        'EXACT_BODY_BYTE_IDENTICAL_TO_FULL_ORIGINAL '+before['original']['sha256']+
        '; duplicate body display omitted, original full reading required.')
    sections=[('original',values['original']),('candidate',candidate_text),
              ('full_diff',delta or '비교한 원문과 선택본문의 바이트 및 줄 차이 없음')]
    framed=''
    for label,text in sections:
        framed+='=== BEGIN '+key+' '+label+' characters='+str(len(text))+' ==='+chr(10)
        framed+=text+chr(10)+'=== END '+key+' '+label+' ==='+chr(10)
    parts=[];rebuilt=[]
    for offset in range(0,len(framed),2000):
        fragment=framed[offset:offset+2000]
        pin=save(OUT/'reading_packets_v1'/(stem+'_'+str(len(parts)+1).zfill(4)+'.txt'),fragment)
        parts.append(dict(pin,characters=[offset,offset+len(fragment)]));rebuilt.append(fragment)
    assert ''.join(rebuilt)==framed
    row={name:before[name] for name in ['id','original_text_sha256','source_ids',
        'source_ids_sha256','input_ids','occurrences','original']}
    row.update(candidate=before['body'],role=item['reviewer'],primary_author_role=before['role'],
        primary_source_cohort=before['cohort'],prior_review=before['review'],
        prior_snapshot=before['snapshot'],source_kind='UNKNOWN_MIXED_NATIVE_CACHE',
        reading_parts=parts,byte_identical_body=same,candidate_is_prior_selected_body=True,
        root_approved=False,cache_admitted=False)
    rows.append(row);by_id[key]=row
    if same:identity.append(key)

known = {
    'expanded_train:1065478':'미존재 도표/이미지를 직접 가리키는 단위와 반복 teaser·댓글의 실제 역할을 확인한다. 완결된 UML 지침/명명 예/조건은 보존하며 끊긴 시연을 그대로 ACCEPT하지 않는다.',
    'expanded_train:56606':'명시 control-Q/P/A/F 등 실제 완전 명령과, 그룹/접두키를 잃고 R/A 등만 반복된 표 행을 구별한다. 누락 접두키를 추정하지 않으며 완결된 튜토리얼·숫자·typo() 호출은 보존한다.',
    'expanded_train:1060968':'인수가 사라진 두 bullet과 미완 argv 설명·축 이름 없는 표를 실제 독립 단위로 HOLD한다. UTF8 XML/명명 API/당시 저자의 수정·불확실성/console 조건을 보존한다.',
    'expanded_train:516640':'WildLearner FREE 강좌 홍보/광고와 일반 면접 Q/A를 구별한다. 원래 Python 버전/주장의 정확성까지 새로 고치지 않으며 실제 map()/range()/xrange() 이름·조건을 보존한다.',
    'expanded_train:1166147':'주석 // 뒤 같은 물리 줄에 붙어 동작 예를 잃은 코드·붙은 두 val 선언을 주의한다. 개행을 추정 생성하지 않는다. 별도로 완결된 :=/+=/++= 설명과 정상 예·키·조건은 보존한다.'}
save(OUT/'ROOT_KNOWN_CONTEXT_FINDINGS_V1.md', '# 총괄의 독립 전문 확인으로 찾은 초기 위험'+chr(10)+
     chr(10).join('- '+key+': '+value for key,value in known.items())+chr(10)+
     '실제 판독 근거: a30e1c/16fb41. 이 다섯 건도 새로운 원문/사실을 생성하지 않고 지정 전문으로 경계를 판단한다.'+chr(10))
reader=AUDIT/'scoped_packet_reader_v1.py'
assert inv.file_sha(reader)=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
for role in roles:
    priority={key:i for i,key in enumerate(priorities[role])}
    assigned[role].sort(key=lambda key:(0,priority[key]) if key in priority else
        (1,len(next(item['values']['original'] for item in prepared if item['row']['id']==key)),key))
    directory=BASE/'agents'/role/GROUP;directory.mkdir(parents=True,exist_ok=False)
    registry=AUDIT/('SCOPED_ROOT12_'+role.upper()+'_INPUTS_V1.json')
    inv.write_json(registry,dict(allowed_packet_directory=str((OUT/'reading_packets_v1').relative_to(ROOT)),
        sources={key:by_id[key]['reading_parts'] for key in assigned[role]}))
    reg_sha=inv.file_sha(registry)
    wrapper=AUDIT/('read_root12_'+role+'_packet_v1.py')
    code='from pathlib import Path'+chr(10)+'import argparse,hashlib,importlib.util,json'+chr(10)
    code+="HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]"+chr(10)
    code+="HELPER=HERE/'scoped_packet_reader_v1.py'"+chr(10)
    code+="assert hashlib.sha256(HELPER.read_bytes()).hexdigest().upper()=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'"+chr(10)
    code+="s=importlib.util.spec_from_file_location('root12_reader',HELPER);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)"+chr(10)
    code+="p=argparse.ArgumentParser();p.add_argument('source_id');p.add_argument('packet',type=int);a=p.parse_args()"+chr(10)
    code+="row=m.read_piece(HERE/"+repr(registry.name)+','+repr(reg_sha)+",ROOT,a.source_id,a.packet,1)"+chr(10)
    code+="print('APPROVED_PACKET '+json.dumps({k:v for k,v in row.items() if k!='text'},ensure_ascii=False));print(row['text'],end='');print(chr(10)+'END_APPROVED_PACKET')"+chr(10)
    save(wrapper,code)
    short=ROOT/'tmp'/('hold-'+('c' if role=='context_controls' else 'l')+'-root12-v1')
    save(short,'#!/usr/bin/env bash'+chr(10)+'exec /home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B '+str(wrapper)+' "$@"'+chr(10))
    start=['# 채택 전 독립 원문/선택본문 교차 판독',
        '역할: '+role+'; 자기 작성 원문은 배정되지 않았다. 한 TASK는 재개 단위이지 전체 작업량 제한이 아니다.',
        '원문/본문/모든 실제 diff를 끝까지 읽어 독립적으로 완결되는지 판단한다. prior candidate는 자동 후보가 아니라 이미 1차 검토한 선택본문이다.',
        '바이트 동일성은 내용 완결·정제 완료 증명이 아니다. 문서 자체의 빈 주체/인수/표 축, 미완 절, 그림/인용 포인터, 광고·추출 혼입도 확인한다.',
        '유효한 이름·값·관계·조건·부정·시점·불확실성·인용 주체·일반 코드는 보존한다. 원문에 없는 함수/수식/개행/글리프/표 축을 만들지 않는다.',
        '입력은 자기 TASK의 정확 original/candidate/packet 및 ROOT_KNOWN_CONTEXT_FINDINGS_V1.md뿐이다. 다른 역할·다른 세션·보호 자료는 금지다.',
        '출력은 이 자기 폴더의 TXT/MD뿐이다. 코드/JSON/시험/계산/Git/웹/GPU/모델은 금지하며 제공된 고정 읽기 reader만 실행 가능하다.',
        '동일 본문이면 전체 원문을 읽고 TASK의 byte identity 근거를 기록해 중복 본문 표시 생략을 사용한다. 변경 본문은 source/body/diff 전량 판독한다.',
        'packet은2000자의 연속 프레임이다. 물리 경계는 손상이 아니다. 출력 잘림은 지정 reader의 해당 packet만 재호출한다.',
        '후보가 전체로 적절하면 ACCEPT_CANDIDATE와 정확 candidate TXT명. 복사하지 않는다. 교정이 필요하면 REVISE_TEXT와 자기 새 TXT, 원형 hold MD.',
        '새 드래프트는 exact candidate에서 아직 없는 ID_counter_working_v1.txt로 cp --no-clobber한 뒤 아직 리뷰에 선택하기 전까지 좁은 패치로 편집 가능하다.',
        '원형/초기후보/기존 선택/기존 리뷰/역사 기록 덮기·삭제·개명·EOF 바이트 절단·sed 시작끝 범위삭제는 금지다. 리뷰 선택 뒤 working TXT도 고정한다.',
        'review_NNN.md: ID/판정/실제 판독 범위/정확 출력/구체 근거 5열의 해당 TASK 전 행. 최종 전체 diff/EOF를 확인하고 선택한다.',
        '미결 의미만 좁게 총괄에게 질문하고 다른 ID를 계속한다. 명백한 빈 형식/문서LF는 기록하고 스스로 처리한다. 같은 원문을 메타 확인 때문에 재독하지 않는다.',
        '검토 메모를 학습 TXT에 섞지 않는다. 새 무기 제작 세부 등 보호 분류를 발견하면 상세 재작성 없이 metadata 사유만 총괄에게 알리고 다른 ID를 계속한다.',
        '독립 재검토는 신규 1차 고유 원문 수에 더하지 않는다. ROOT·캐시·학습 채택 권한은 없다.',
        '읽기 명령: bash '+str(short)+' expanded_train:ID PACKET_NUMBER',
        '추가 기준: '+str(OUT/'ROOT_KNOWN_CONTEXT_FINDINGS_V1.md')]
    save(directory/'START_HERE.md',chr(10).join(start)+chr(10))
    for task,offset in enumerate(range(0,len(assigned[role]),5),1):
        lines=['# TASK_'+str(task).zfill(3),'START_HERE 계약을 따른다.']
        for key in assigned[role][offset:offset+5]:
            row=by_id[key];lines += ['## '+key,'original: '+str(ROOT/row['original']['path']),
                'candidate: '+str(ROOT/row['candidate']['path']),
                '원형/선택본문 byte-identical: '+str(row['byte_identical_body']),
                '원형 SHA: '+row['original']['sha256'],'선택본문 SHA: '+row['candidate']['sha256'],
                '전체 읽기 packet: '+str(len(row['reading_parts'])),
                *['- '+str(ROOT/pin['path']) for pin in row['reading_parts']]]
        save(directory/('TASK_'+str(task).zfill(3)+'.md'),chr(10).join(lines)+chr(10))
manifest=dict(status='EXACT_PRIOR_BODIES_INDEPENDENT_COUNTER_REQUIRED_NOT_ADMISSION',
    rows=rows,assignments=assigned,source_characters_by_role=dict(costs),
    prior_first_review_sources=3688,new_first_review_credit=0,
    source_code_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [Path(__file__),reader]},
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [preflight_path,records_path,guard_path,frozen,
        AUDIT/'ROOT12_INDEPENDENT_COUNTER_SCOPE_V1.md']},
    original_author_counter_self_overlap=0,deferred_to_primary_followups=sorted(deferred),
    identity_original_read_required=identity,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(OUT/'manifest.json',manifest)
report=dict(status=manifest['status'],sources=len(rows),positions=sum(r['occurrences'] for r in rows),
    assignments={role:dict(sources=len(ids),tasks=(len(ids)+4)//5,first_id=ids[0]) for role,ids in assigned.items()},
    byte_identical_originals=len(identity),original_author_counter_self_overlap=0,
    source_packet_parts=sum(len(row['reading_parts']) for row in rows),
    manifest=dict(path=str((OUT/'manifest.json').relative_to(ROOT)),sha256=inv.file_sha(OUT/'manifest.json')),
    reused_save_function_only=True,reused_historical_top_level_executed=False,
    new_first_review_credit=0,root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'ROOT12_INDEPENDENT_COUNTER_PREPARED_V1.json',report)
print(json.dumps(report,ensure_ascii=False))
