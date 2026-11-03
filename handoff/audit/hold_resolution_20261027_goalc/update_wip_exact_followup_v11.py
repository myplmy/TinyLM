"""Keep actual checkpoints, prepared inputs, and unread content separate."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

metrics=inv.cache.read(AUDIT/'REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json')
assert metrics['remaining_hold']==110173 and metrics['unprocessed_unique']==70192
receipt=inv.cache.read(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V4.json')
assert receipt['commit']=='42ca61d0b10e85ab5507d48cca9450563b7a2c9f'
assert receipt['whole_changed_path_set_exact'] and receipt['all_committed_bytes_match']
assert receipt['remaining_shared_index_count']==0
field=inv.cache.read(AUDIT/'REMAINING_FIELD_TITLE_READER_PREPARATION_VERIFIED_V1.json')
assert field['unique_sources']==18237 and field['new_file_size_check']['files']==91524
other=inv.cache.read(inv.BASE/'remaining_other_types_full_sources_v1/complete.json')
assert other['counts']==dict(queued_unique=50162,queued_positions=77879) and len(other['pages'])==98
start=AUDIT/'REMAINING_OTHER_TYPES_NATIVE_PROCESS_STARTED_V1.json'
assert start.exists()
exit_path=AUDIT/'REMAINING_OTHER_TYPES_NATIVE_PROCESS_EXIT_V1.json'
state='다른유형50162의 실제CPU native준비는 자체세션61671/로그/STARTED로 RUN관측 중이며 종료와전량일치는 아직미확인이다.'
if exit_path.exists():
    process=inv.cache.read(exit_path)
    state='다른유형50162 native준비의 실제 종료코드는'+str(process['process_exit_code'])+'이며 내용판독·채택은별도다.'
work=(
    '전체 정제 goal active/1번RUN이다. 공식 cache_reviewed_partial_v3는 실제생성0/별도독립consumer0/전체계측 완료다. '
    '원래H460695 중K32187/E195071/X123264/H110173이며 H는개별검토38/미처리110135위치(70192고유)로분리한다. '
    'v2대비H5353감소,채택1372548문서/EOS포함1066879306IDs/본문1065506758IDs다. 기준1145290본문보존·채택전량재생성·경계/EOS/직렬화·파일20MB미만·정확중복0/trainval정확교집합0은그검증범위다. '
    '원래H 제외123264는정확중복123177/개별문맥84/원형경계3이며불량확정과중복을섞지않는다. 출처UNKNOWN/근접·이동구간·URL누설미확인은유지한다. '
    'ROOT11선택7857과출생2743전량저장은중간근거이며출생별도2차전문판독은미완이다. '
    'literal snapshot8은1793중1050행저장/743미저장,1000본문후보/50중재이며채택이아니다. 저장행은미판독명령질문도포함하므로전량내용판독수로바꾸지않는다. '
    '잘못된TASK025/026리뷰를별도새버전으로연결중이며원문/후보다른controls26의정확명령22TASK분을추가해미판독질문을회수하고있다. '
    '공식미처리70192는literal1792+필드제목18237+나머지50162+보호metadata1로전량추적한다. '
    '필드제목18237의native전량일치와36페이지읽기준비를완료했고91524새파일모두20MB미만,최대2981385바이트다. 동일8749/상이9488,고정reader경계4934/타역할거부36/실제wrapper0의36페이지를확인했다. '
    '기존5Luna는literal72까지와과거중재연결후자기필드제목page001–036전량을이어가도록정확큐/허용범위를전달했다. '
    +state+
    ' primary발행처로DDI11labels/Angular3Input표기/ROUND표제/random세지수/PEP5인덱스와실제코드주석을대조해Luna복원근거를주었다. 새본문채택은별도검산전이다. '
    '한국어중간저장42ca61d0의2143명시경로/22753652바이트·부모·전체blob·당시index0검산을완료하고Git창을닫았다. 그뒤새중재/작업은미저장이며전체own-clean을주장하지않는다. '
    '전체미처리정제·독립의미검토·정본연쇄·최종핸드오프는미완이다. 보호7부모/동일SHA11은metadata/승인safeview만사용하며GPU/모델/학습/추가300M/push/PR금지다.')
resume=(
    '자체세션61671와로그/STARTED/EXIT로50162 native준비의실제종료를회수하고일치수를검산한다. 실패출력은보존하고새버전으로만교정한다. '
    '다섯Luna는literal전량/과거중재를정확새리뷰로연결한뒤ROOT_FIELD_PHASE_DISPATCH와자기큐에따라36페이지전량을계속한다. '
    '총괄은남은좁은질문·오삭제/코드단편과손상구조/숫자·인용·귀속·실제ID/본문/sidecar결합을검토한다. '
    '나머지50162도98페이지전량의지정읽기입력을기존준비기로재사용해다음순차큐를만든다. '
    '검토완료선택은새ROOT/roster/별도캐시생성/독립consumer/전체계측으로닫되기존검증캐시를덮지않는다. '
    '전량독립의미검토와발견오류조치및정본/최종핸드오프/명시한국어로컬저장은계속필요하다. '
    '중간저장·부분캐시·압축은goal정지/일시중지사유가아니다. A–E전체조건충족때만완료한다.')
names=['EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V4.json','REMAINING_FIELD_TITLE_READER_PREPARATION_VERIFIED_V1.json',
       'REMAINING_FIELD_TITLE_READING_CONNECTIONS_V1.json','REMAINING_OTHER_TYPES_NATIVE_PROCESS_STARTED_V1.json',
       'CONTROLS_SEPARATE_LITERAL_COMMANDS_V1.json','PRIMARY_PEP227_EXACT_RECOVERY_EVIDENCE_V1.json']
links='; '+'; '.join(str((AUDIT/name).relative_to(ROOT)) for name in names)
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
for field,value in {'작업 내용':work,'산출물':links,'이어받을 지점':resume}.items():
    lines=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines)==1
    before=lines[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    process=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override',
        '--file',str(ledger),'--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','검증cache3와중간저장42ca 및전량필드준비/다른유형50162RUN을구분해기록',
        '--approval-ref','사용자전체잔여HOLD정제및objective CPU/파생데이터/코드시험/문서/한국어로컬저장허가'],
        cwd=ROOT,text=True,capture_output=True)
    if process.returncode:print(process.stdout,process.stderr);raise SystemExit(process.returncode)
    print(field,'CAS 완료')
