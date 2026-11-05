"""Apply six exact cells through the official WIP API; keep all goals running."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]; AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import wip

path=ROOT/'handoff/WIP_20261027_작업원장.md'
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='BA8725BAD2F45F00FD166C7028B9576BDAA9E491D49335514EB79AEF97D8CC90'
table=wip.parse_table(raw.decode('utf-8')); rows={r[1]:r[2] for r in table.rows}
assert len(rows)==9 and rows['1'][2]==rows['7'][2]==wip.RUN
prior=json.loads((AUDIT/'WIP_EXACT_FOLLOWUP_V71_PLAN.json').read_bytes())
for update in prior['updates']:
    assert rows[update['item']][table.header.index(update['field'])]==update['after']
other=[r[2] for r in table.rows if r[1] not in {'1','7'}]
other_sha=hashlib.sha256(json.dumps(other,ensure_ascii=False,separators=(',',':')).encode()).hexdigest().upper()
assert other_sha=='B7BAAC73EC093EAB2B9AB8D24FAD948731FCBCCF78C4FD391ABECC5004A56FB6'

values={
 ('1','작업 내용'):'진행: 전체 정제 A–E는 미완료다. 공식 cache15는 build/consumer 실제 exit0·독립검산으로 HOLD105824이며 최초110173보다4349위치 감소다. ROOT32/roster23 기대104894와 반영대기930위치는 공식 감소와 구분한다. 이전30만 처리 코드를 재확인해 사례·반례→좁은 규칙→회귀→전량/변경분 적용→독립검증 방식으로 복귀했다. 개별 전문 재독 위주로 흐른 총괄의 진행 방식 오류를 인정했다. 새 policy27은382회귀 PASS, 남은66411고유 대기열을 분석해478고유/577위치 후보를 찾았다. 독립 문자보존 검산은478개 전부 통과했고 반례10개 PASS다. 기존 독립 전문리뷰24개와15개 완전동일/9개 끝줄바꿈만 다름을 대조했다. 319241의 유효 acques Perrin 오삭제를 실제 원문/diff로 찾아 author 새v4에서 복원했다. 454개 후보를 개별 인간 전문판독으로 세지 않으며 아직 규칙 후보 ROOT/캐시 채택0이다. V13 동결계수는 실제 최초리뷰6998고유/12987위치, 최초미검토63194고유/97148위치다. guard5 원형 접근0, opaque23 top-level join과 runtime8 현재193핀 선결은 완료했으나 cache16 build/consumer는 NOT_RUN이다. 실제 마지막 로컬저장은V27 4fb1fd94이며 이후 변경은 V28 저장 준비 중이다.',
 ('1','산출물'):'handoff/audit/hold_resolution_20261027_goalc/PREVIOUS_BULK_METHOD_VS_CURRENT_20261105_V1.md; handoff/audit/hold_resolution_20261027_goalc/RULE27_DECLARED_NAME_LIST_CENSUS_V1.json; handoff/audit/hold_resolution_20261027_goalc/RULE27_LITERAL_DELTA_INDEPENDENT_VERIFIED_V1.json; handoff/audit/hold_resolution_20261027_goalc/RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V2.json; handoff/audit/hold_resolution_20261027_goalc/HOLD_110173_STAGNATION_DIAGNOSIS_V13.json; handoff/audit/hold_resolution_20261027_goalc/CACHE_V8_ROOT32_RUNTIME_PIN_PREFLIGHT_V1.json',
 ('1','이어받을 지점'):'현재 검증된478규칙 후보는 최신 개별 NEEDS_ROOT와 기존 선택 중복을 다시 제외해 소스별 증거/정제본문 SHA를 연결하고 일괄 채택한다. 개별 전문판독과 규칙 검증을 별도 계수하며 ROOT32 대기930 및 counter39 새완료분을 함께 반영한다. 충분히 모은 최종 ROOT에 roster 전체검산·opaque·참조census·현재핀을 맞춘 뒤 cache16을 하나만 생성/검증한다. V28 한국어 명시 로컬 저장을 수행하고 전체 정제를 계속한다. 847961/89859의 primary 기반 정확 숫자·순서 closure와 새 NEEDS_ROOT 경계 중재도 병행한다. 원형·기존cache11/15·로그·guard5 11ID/14SHA/19alias·3안전파생본문을 보존한다. GPU/모델/추가300M/push/PR은 실행하지 않으며 전체 A–E 이전 완료·일시중지 금지.',
 ('7','작업 내용'):'진행: 다섯 Luna는 현재 V6 정확 배정으로 field12~36의 실제 전문판독·새 TXT/MD를 계속한다. C/L은 오래된 root12 이중검토를 끝까지 기다리는 병목을 풀고 field12 최초검토를 우선하며 미완료 커서를 남겼다. counter39 실제2994행=C1574/L1420, 미완694이며 C의913040 누락은 완료로 만들지 않았다. field12v13/14v8/15v4/16v3는 오류0이고 H는16/J는15/G는14/C·L은12를 진행한다. 이름252081과315183의 생략주어는 앞 문맥으로 해석되는 유효 서술로 복원했으며318592의 일본 연호 날짜도 보존했다. UTF8 마지막바이트 자르기는 금지하고 실제 LF를 허용한다. source/candidate 동일성은 내용품질로 읽지 않는다. 원문/후보/packet 사본과266MB ledger 복제를 억제하며 새 선택은512행/4MB 이하 조각을 재사용한다. 새 정책 후보는 프로그램 산출물로 명시하고 Luna 개별 전문검토로 위장하지 않는다.',
 ('7','산출물'):'handoff/audit/hold_resolution_20261027_goalc/RESUME_REMAINING_FIELD_ROLE_BINDINGS_V2.json; handoff/audit/hold_resolution_20261027_goalc/SELECTION_METADATA_SHARDING_F3_F4_V1.md; handoff/audit/hold_resolution_20261027_goalc/RESUME_HOLD_REFERENCE_STORAGE_V1.md; handoff/audit/hold_resolution_20261027_goalc/RESUME_OUTPUT_EXISTENCE_AND_DRAFT_SCOPE_V1.md; handoff/audit/hold_resolution_20261027_goalc/ROOT12_COUNTER_SNAPSHOT_V39_RUN_V1.log; tmp/COORD_HOLD_01a17740.md',
 ('7','이어받을 지점'):'다섯 역할은 자기 PROGRESS의 다음 TASK부터 계속하며 단순 미완료표기·문장 생략주어·주제어만으로 HOLD를 확대하지 않는다. 250303 수식 직접 종속 구절 경계와412272 등 실제 불명 문맥은 총괄이 전문 중재한다. 기존 끝낸 페이지를 재독하거나 단순 끝줄바꿈만으로 새버전을 만들지 않는다. 의미/판정/SHA/경로 변경은 새버전으로 보존한다. 새 중간물은 필요한 변경 본문과 작은 증거만 저장하고 대량 원문·후보·캐시 복제를 피한다. 이후 other 대기열은 정확 binding 후 진행한다. 전체 정제는 RUN이다.',
}
updates=[dict(item=item,field=field,before=rows[item][table.header.index(field)],after=value)
    for (item,field),value in values.items()]
plan=dict(status='EXACT_OWN_WIP_CAS_PLAN_V72_ORIGINAL_BULK_METHOD_RESUMED',wip=str(path.relative_to(ROOT)),
    session_id='01a17740-f435-7243-874c-2b5d58181c4c',before_sha256=hashlib.sha256(raw).hexdigest().upper(),
    other_rows_sha256=other_sha,updates=updates,goal_complete=False,training_authorized=False)
with (AUDIT/'WIP_EXACT_FOLLOWUP_V72_PLAN.json').open('xb') as f:
    f.write((json.dumps(plan,ensure_ascii=False,indent=2)+chr(10)).encode())
for update in updates:
    subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(path),
        '--item',update['item'],'--field',update['field'],'--expect-before',update['before'],
        '--set-after',update['after'],'--reason','진행 상태를 유지하며 실제 검증/잔여량과 원래 대량 규칙 방법 복귀를 최신 근거로 교정한다.',
        '--approval-ref','현재 사용자 전체 잔여 HOLD 정제 계속 및 원래30만 처리 방법 확인 지시'],check=True,stdout=subprocess.DEVNULL)
new=path.read_bytes(); updated=wip.parse_table(new.decode())
after_rows={r[1]:r[2] for r in updated.rows}
assert [r[2] for r in updated.rows if r[1] not in {'1','7'}]==other
assert after_rows['1'][2]==after_rows['7'][2]==wip.RUN
for update in updates:assert after_rows[update['item']][updated.header.index(update['field'])]==update['after']
subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--capsule-check','--file',str(path)],check=True)
receipt=dict(status='OFFICIAL_WIP_SIX_EXACT_CAS_UPDATES_VERIFIED',wip=str(path.relative_to(ROOT)),
    sha256=hashlib.sha256(new).hexdigest().upper(),bytes=len(new),updates=len(updates),
    other_rows_preserved_exactly=True,goal_and_authoring_rows_still_running=True,
    plan=dict(path=str((AUDIT/'WIP_EXACT_FOLLOWUP_V72_PLAN.json').relative_to(ROOT)),
        sha256=hashlib.sha256((AUDIT/'WIP_EXACT_FOLLOWUP_V72_PLAN.json').read_bytes()).hexdigest().upper()))
with (AUDIT/'WIP_EXACT_FOLLOWUP_V72_APPLIED.json').open('xb') as f:
    f.write((json.dumps(receipt,ensure_ascii=False,indent=2)+chr(10)).encode())
print(json.dumps(receipt,ensure_ascii=False))
