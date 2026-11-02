"""Resume only the assigned source through exact small immutable views."""
from datetime import datetime,timezone
from pathlib import Path
import json
import stat
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE=inv.BASE
GROUP=BASE/'repeat_named_full_independent_v1'
manifest_path=GROUP/'manifest.json'
note_path=BASE/'agents/context_hangul/repeat_named_full_independent_v1/path_error_note_v1.md'
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
manifest=inv.cache.read(manifest_path)
source=next(row for row in manifest['rows'] if row['id']=='expanded_train:1008072')
inv.require(source['role']=='context_hangul' and source['id'] not in contract['restricted_ids'] and
    source['original_text_sha256'] not in contract['restricted_hashes'],'exact unrestricted assigned source required')
out=GROUP/'fixed_read_1008072_1500_v1'
runbook=BASE/'agents/context_hangul/repeat_named_full_independent_v1/ROOT_READ_1008072_1500_V1.md'
receipt=AUDIT/'FIXED_READER_1008072_SCOPE_RECEIPT_V1.json'
inv.require(not out.exists() and not runbook.exists() and not receipt.exists(),'new fixed reader namespace required')

# Only lstat metadata for the two reported paths, never their contents or hashes.
wrong=BASE/'agents/context_hangul/repeat_named_full_independent_v1/inputs'
observed=[]
for label in ('original','candidate'):
    path=wrong/('expanded_train_1008072_'+label+'.txt')
    try:
        value=path.lstat()
        observed.append(dict(path=str(path.relative_to(ROOT)),exists_now=True,
            symlink=stat.S_ISLNK(value.st_mode),regular_file=stat.S_ISREG(value.st_mode)))
    except FileNotFoundError:
        observed.append(dict(path=str(path.relative_to(ROOT)),exists_now=False))

for label in ['original','candidate']:
    pin=source[label]
    inv.require(inv.file_sha(ROOT/pin['path'])==pin['sha256'],'approved original/candidate pin changed')
fragments=[]
for pin in source['reading_parts']:
    path=ROOT/pin['path']
    inv.require(inv.file_sha(path)==pin['sha256'],'approved shared reading packet changed')
    fragments.append(path.read_text(encoding='utf-8'))
framed=''.join(fragments)
inv.require(framed.startswith('=== BEGIN expanded_train:1008072 original characters='),
            'approved framing differs from the assigned source')
out.mkdir()
parts=[]
for offset in range(0,len(framed),1500):
    text=framed[offset:offset+1500]
    path=out/('approved_part_'+str(len(parts)+1).zfill(3)+'.txt')
    payload=text.encode('utf-8')
    inv.require(0<len(payload)<20_000_000,'view must be bounded')
    with path.open('xb') as stream:
        stream.write(payload)
    parts.append(dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),
                      characters=[offset,offset+len(text)]))
inv.require(''.join((ROOT/p['path']).read_text(encoding='utf-8') for p in parts)==framed,
            'all fixed views must reconstruct the exact approved full framing')
lines=['# 1008072 지정 원문만 재판독하는 고정 경로','',
 '아래1500자 조각은 원래 지정한 지정 shared6000자 전체 패킷를 같은 순서/내용으로 재분할한 것이다. 원문·후보·전체 diff는 바뀌지 않았다. 잘못 보고된 경로는 재열람하지 않는다.','',
 '이 MD와 아래 정확 새 TXT 경로를 읽기 허용 입력에 추가한다. 쓰기는 기존 자기 역할 폴더의 새 TXT/MD만이다. 명령의 경로를 그대로 복사하고 agents 접두/../·변수·루프로 재구성하지 않는다. 코드·해시·통계·Git·웹·모델·다른 자료는 계속 금지다.','',
 '각 명령은 한 조각을 읽는다. max_output_tokens는8000으로 둔다. 도구가 실제 truncation 경고를 붙였는지와 정상적인 파일끝을 구별한다. 조각의 끝이 단어 중간이거나 BEGIN/END가 없을 수 있으며 이는1500자 연속분할의 정상 결과다.','',
 '모든 조각을 순서대로 읽어 original/candidate/full_diff의 각 논리 END와 마지막 실제 EOF까지 확인한다. 한 조각에 전체 original END가 없다는 이유만으로 도구 잘림이라고 쓰지 않는다. 실제 잘림 경고/문구가 나오면 그 조각을 완료로 세지 말고 총괄에 정확 번호를 보낸다.','',
 '이전 잘못된 경로의 내용 반환 보고는 독립 확인되지 않았다. 이 자료로 그 보고를 성공/차단으로 바꾸지 않으며, 아직1008072 리뷰/본문이 없다는 기록을 보존한다. 이번 새 판독 뒤에만1008072의 실제 새 TXT/MD와 정확5행 교정 리뷰를 작성한다.','']
for number,pin in enumerate(parts,1):
    lines.extend(['## 조각 '+str(number).zfill(3),'',
        "`cat -- '"+str(ROOT/pin['path'])+"'`",''])
with runbook.open('x',encoding='utf-8') as stream:
    stream.write(chr(10).join(lines))
result=dict(status='EXACT_ASSIGNED_SOURCE_FIXED_READER_READY_REPORTED_OTHER_PATH_CONTENT_UNVERIFIED',
    utc=datetime.now(timezone.utc).isoformat(),id=source['id'],role='context_hangul',
    approved_original=source['original'],approved_candidate=source['candidate'],
    original_shared_packets=len(source['reading_parts']),fixed_parts=parts,
    framed_sha256=inv.sha(framed),reported_wrong_path_lstat_only=observed,
    reported_wrong_contents_read_by_root=False,reported_wrong_contents_hashed_by_root=False,
    earlier_content_report_independently_confirmed=False,
    admission_from_this_source=0,goal_complete=False,training_authorized=False,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in
        [manifest_path,note_path,runbook,Path(__file__)]})
inv.write_json(receipt,result)
print(json.dumps(dict(status=result['status'],fixed_parts=len(parts),
    reported_wrong_paths_exist_now=sum(row['exists_now'] for row in observed),
    wrong_path_contents_read=0,cache_admitted=0),ensure_ascii=False))
