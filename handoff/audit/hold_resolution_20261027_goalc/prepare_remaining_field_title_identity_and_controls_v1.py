"""Reuse exact-input and fixed-reader contracts for every prepared field page."""
from collections import Counter
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards
from identical_input_reading_v1 import digest,prove_identical
from scoped_packet_reader_v1 import read_piece

BASE=inv.BASE
source_path=BASE/'remaining_field_title_readers_v1/complete.json'
source=inv.cache.read(source_path)
assert source['sources']==18237 and len(source['pages'])==36
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract=inv.cache.read(contract_path)
blocked_ids=set(contract['restricted_ids'])
blocked_hashes=set(contract['restricted_hashes'])
test_path=AUDIT/'IDENTICAL_INPUT_READING_TEST_RESULT_V1.json'
test=inv.cache.read(test_path)
assert test['process_exit_code']==0
assert inv.file_sha(ROOT/test['test'])==test['test_sha256']
assert inv.file_sha(ROOT/test['log'])==test['log_sha256']
helper_path=AUDIT/'scoped_packet_reader_v1.py'
assert inv.file_sha(helper_path)=='DCEB4BD2CB9ABD8681ACEE9F2604B69D55625B20D28BCB1956C7B99E3E1D96A6'
wrapper_path=AUDIT/'read_context_controls_birth_packet_v1.py'
wrapper=wrapper_path.read_text(encoding='utf-8')
roles=['context_controls','context_hangul','context_latin','historical_review','legacy_review']
queues={role:[] for role in roles}
totals=Counter()
page_results=[]
result_path=AUDIT/'REMAINING_FIELD_TITLE_READING_CONNECTIONS_V1.json'
assert not result_path.exists()

def save(path,text):
    data=text.encode('utf-8')
    assert 0<len(data)<20_000_000
    with path.open('xb') as stream:stream.write(data)
    return dict(path=str(path.relative_to(ROOT)),sha256=digest(data),bytes=len(data))

def save_json(path,value):
    return save(path,json.dumps(value,ensure_ascii=False,indent=2)+chr(10))

def read(pin,allowed):
    path=ROOT/pin['path']
    assert not path.is_symlink() and path.resolve().is_relative_to(allowed.resolve())
    data=path.read_bytes()
    assert digest(data)==pin['sha256']
    return data

for page in source['pages']:
    manifest_path=ROOT/page['path']
    assert inv.file_sha(manifest_path)==page['sha256']
    manifest=inv.cache.read(manifest_path)
    group=page['group']
    out=BASE/group
    rows=manifest['rows']
    assert not ({r['id'] for r in rows}&blocked_ids)
    assert not ({r['original']['sha256'] for r in rows}&blocked_hashes)
    native=BASE/'remaining_field_title_native_proofs_v1/pages'/('page_'+str(page['page']).zfill(3))/'inputs'
    controls=[r for r in rows if r['role']=='context_controls']
    registry_path=AUDIT/('SCOPED_CONTEXT_CONTROLS_FIELD_PAGE_'+str(page['page']).zfill(3)+'_INPUTS_V1.json')
    registry=dict(allowed_packet_directory=str((out/'reading_packets_v1').relative_to(ROOT)),
                  sources={r['id']:r['reading_parts'] for r in controls})
    registry_pin=save_json(registry_path,registry)
    reader_path=AUDIT/('read_context_controls_field_page_'+str(page['page']).zfill(3)+'_packet_v1.py')
    reader=wrapper.replace('SCOPED_CONTEXT_CONTROLS_BIRTH_INPUTS_V1.json',registry_path.name)
    reader=reader.replace('BCE445B7C4897A75926EAC3618D5EFBC8E5F371EC71D891E1B41966F36F0A588',registry_pin['sha256'])
    assert reader.count(registry_path.name)==1 and reader.count(registry_pin['sha256'])==1
    reader_pin=save(reader_path,reader)
    by_id={r['id']:r for r in rows}
    proofs={}
    counts=Counter()
    for row in rows:
        original=read(row['original'],native)
        candidate=read(row['candidate'],native)
        if original!=candidate:
            assert row['original']['sha256']!=row['candidate']['sha256']
            proofs[row['id']]=dict(protocol='SEPARATE_COMPLETE_READING_REQUIRED',id=row['id'],
                original=row['original'],candidate=row['candidate'])
            counts['nonidentical_sources_full_separate_reading']+=1
            continue
        packets=[dict(pin,payload=read(pin,out/'reading_packets_v1')) for pin in row['reading_parts']]
        proof=prove_identical(row['id'],original,candidate,row['original']['sha256'],row['candidate']['sha256'],packets)
        proofs[row['id']]=dict(proof,id=row['id'],original=row['original'],candidate=row['candidate'])
        counts['byte_identical_sources']+=1
        counts['all_packet_parts']+=len(packets)
        counts['required_packet_parts']+=len(proof['required_packets'])
        counts['duplicate_only_packet_parts']+=len(proof['duplicate_only_packets'])
    # Actually exercise the fixed registry's bounded reader on both sequence ends.
    for row in controls:
        for number in sorted({1,len(row['reading_parts'])}):
            piece=read_piece(registry_path,registry_pin['sha256'],ROOT,row['id'],number,1)
            assert piece['path']==row['reading_parts'][number-1]['path'] and piece['packet_complete']
            counts['actual_fixed_reader_boundary_checks']+=1
    other=next(r for r in rows if r['role']!='context_controls')
    try:
        read_piece(registry_path,registry_pin['sha256'],ROOT,other['id'],1,1)
    except ValueError as error:
        assert str(error)=='source is outside this role assignment'
        counts['actual_other_role_source_rejected']+=1
    else:
        raise AssertionError('reader allowed a different role source')
    process=subprocess.run([sys.executable,'-I','-B',str(reader_path),'--source-id',controls[0]['id'],
        '--packet','1','--piece','1'],cwd=ROOT,capture_output=True,text=True)
    assert process.returncode==0 and process.stdout.startswith('APPROVED_PACKET_PIECE ')
    assert process.stdout.endswith('END_APPROVED_PACKET_PIECE'+chr(10))
    counts['actual_fixed_wrapper_exit_zero']+=1
    plans=[]
    for role,assigned in manifest['assignments'].items():
        directory=BASE/'agents'/role/group
        covered=set()
        for task in sorted(directory.glob('TASK_*.md')):
            ids=sorted(safeguards.explicit_task_ids(task.read_text(encoding='utf-8')))
            assert ids and set(ids)<=set(assigned) and not (set(ids)&covered)
            covered.update(ids)
            lines=['# 정확 입력 전문 판독 연결 '+task.stem,'',
                '총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.',
                '같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.',
                '이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.',
                '아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.',
                '패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.',
                '새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.',
                '모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.','']
            for ident in ids:
                row=by_id[ident]
                proof=proofs[ident]
                lines+=['## '+ident,'original SHA-256: '+row['original']['sha256'],
                        'candidate SHA-256: '+row['candidate']['sha256']]
                if proof['protocol']!='EXACT_IDENTICAL_INPUT_READING_V1':
                    lines+=['서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.','']
                    continue
                lines+=['원문 frame 패킷: '+str(proof['original_packets']),
                        '최종 full_diff 패킷: '+str(proof['full_diff_packets']),
                        '원문 전문+최종diff 필수 패킷: '+str(proof['required_packets']),
                        '후보 중복만 있는 생략 가능 패킷: '+str(proof['duplicate_only_packets']),'```bash']
                if role=='context_controls':
                    lines+=['/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B '+str(reader_path)
                        +' --source-id '+ident+' --packet '+str(number)+' --piece 1' for number in proof['required_packets']]
                else:
                    paths=[str(ROOT/row['reading_parts'][number-1]['path']) for number in proof['required_packets']]
                    lines+=['cat '+' '.join(paths[offset:offset+2]) for offset in range(0,len(paths),2)]
                lines+=['```','실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.','']
            plans.append(dict(save(directory/('ROOT_IDENTITY_'+task.stem+'_V1.md'),chr(10).join(lines)+chr(10)),role=role,ids=ids))
        assert covered==set(assigned)
        queues[role].append(dict(page=page['page'],group=group,sources=len(assigned),
            start=str(directory/'START_HERE.md'),first=str(directory/'TASK_001.md'),
            identity=str(directory/'ROOT_IDENTITY_TASK_001_V1.md')))
        if role=='context_controls':
            scope=['# 이 페이지의 고정 입력 도구 허가','',
                '현재 literal 전량 배정을 마친 뒤 총괄이 이 페이지 착수를 알리면 사용한다.',
                '자기 START/TASK/READING_VIEWS/ROOT_IDENTITY와 이 MD 및 자기 새 TXT/MD만 literal cat으로 읽을 수 있다.',
                '실제 원문/후보/diff packet은 아래 고정 reader만 사용한다. 다른 Python/코드/registry/raw cat/sed/rg/find 접근은 금지다.',
                '이 실행은 총괄이 고정한 읽기 도구 예외이며 코딩·시험·해시 계산 권한이 아니다.',
                '명령에서 자기 실제 source-id/packet만 고른다. 2000문자 패킷이므로 piece는1이다. 출력예산8000 이상이며 END를 실제 확인한다.',
                '/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B '+str(reader_path)
                    +' --source-id '+controls[0]['id']+' --packet 1 --piece 1',
                '동일입력 계획이 있는 source만 중복 후보 패킷을 생략한다. 원문 전문과 최종diff는 필수다.',
                '실제 새 정제 본문과 sidecar/리뷰만 자기 폴더에 저장한다. 누락값 생성·기존파일 덮기/삭제·다른 역할 접근은 금지다.']
            save(directory/'ROOT_SCOPED_INPUT_READER_V1.md',chr(10).join(scope)+chr(10))
    proof_pin=save_json(out/'identity_reading_proofs_v1.json',dict(status='EXACT_INPUT_LINKS_NOT_MEANING_APPROVAL',
        counts=dict(counts),rows=list(proofs.values()),plans=plans,manifest=page,
        controls_reader=reader_pin,controls_registry=registry_pin,goal_complete=False,training_authorized=False))
    page_results.append(dict(page=page['page'],group=group,sources=len(rows),proof=proof_pin,counts=dict(counts)))
    totals.update(counts)
for role,queue in queues.items():
    lines=['# 필드·제목 유형 전량의 다음 배정 순서','',
        '현재 literal TASK072까지 처리하고 남은 좁은 중재를 정확 리뷰로 연결한 뒤, 총괄이 허용한 페이지부터 시작한다.',
        '36페이지 전량이 후속 범위다. 각 페이지/TASK는 분할 단위이며 전체 작업량 상한이 아니다.',
        '정확 START/TASK/ROOT_IDENTITY를 읽고 지정 원문 전문을 실제 판독한다. controls는 페이지 고정 reader 허가 MD도 먼저 읽는다.',
        '새 TXT/MD 쓰기는 각 해당 자기 역할/페이지 폴더뿐이다. 코드·시험·해시·웹·Git·모델·GPU·다른 역할/보호자료는 금지다.','']
    for item in queue:
        lines+=['## 페이지 '+str(item['page'])+' / '+str(item['sources'])+'고유',
                'START: '+item['start'],'첫 TASK: '+item['first'],'동일입력 계획: '+item['identity']]
        if role=='context_controls':lines+=['고정 reader 허가: '+str(BASE/'agents'/role/item['group']/'ROOT_SCOPED_INPUT_READER_V1.md')]
    save(BASE/'agents'/role/'REMAINING_FIELD_TITLE_QUEUE_V1.md',chr(10).join(lines)+chr(10))
assert sum(page['sources'] for page in page_results)==18237
save_json(result_path,dict(status='ALL_FIELD_READING_LINKS_READY_NOT_CONTENT_READ',sources=18237,pages=page_results,
    counts=dict(totals),input_pins={str(path.relative_to(ROOT)):inv.file_sha(path)
        for path in [source_path,contract_path,test_path,helper_path,wrapper_path,AUDIT/'identical_input_reading_v1.py',Path(__file__)]},
    protected_parent_bodies_opened=0,cleaned_prose_authored_by_root=0,goal_complete=False,training_authorized=False))
print(json.dumps(dict(sources=18237,pages=len(page_results),counts=dict(totals),cache_admitted=0)))
