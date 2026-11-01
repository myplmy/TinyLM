"""Restore all canonical handoff tables without changing any checker rules."""
from pathlib import Path
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).parent
TARGET=ROOT/'handoff/202611011123_HANDOFF.md'


def main():
    receipt=BASE/'HANDOFF_UPDATE_v3.json'
    assert not receipt.exists(),'one-shot handoff patch only'
    before=TARGET.read_text()
    snapshot=BASE/'handoff_before_contract_fix_v2.txt'
    assert not snapshot.exists();snapshot.write_text(before)
    text=before.replace('### 2.1 코드·검증 범위','''### 2.0b 관측에서 사용자 행동으로

| 관측 | 의미 | 사용자 영향 | 다음 행동 |
|---|---|---|---|
|Tiny MMLU약23~25%, Falcon32~34%|현재 분별력 격차가 남음|새 지능 개선 모델로 안내하지 않음|정제 후 본학습과 실제 답으로 검증|
|문서/디스크·새 프로세스 exact|전체 상태를 재현할 기술 기반 확보|향후 재개시 상태 누락을 줄일 수 있음|실제 승인 원천·제품 CLI 연결|
|동어휘 KL비용+33.34%|교사 연결은 무료가 아님|예산·메모리에서 추가 비용을 예상|좋은 교사와 본학습 효과는 별도 검증|
|현재 전체 smoke 미실행|새 코드의 종합 증거는 없음|부분 검사와 전수 통과를 구별|공유 collector 승인 후 새 전체 실행|

### 2.1 코드·검증 범위''',1)
    addition='''### 3.1 정본 동기화

| 산출물 | 필요 여부 | 실제 diff | 미갱신 사유 |
|---|---|---|---|
|결과101/107·실험목록|필요|579·15~17절/원로그50·행 갱신|해당 없음|
|P106B/P107·실험계획목록|필요|실제 완료·미완·완료 SH 연결|해당 없음|
|기준표·METHODS·03/05·COMPASS|필요|정본 결과 링크·판정 범위 갱신|해당 없음|
|WIP·현재 인계|필요|51/105완료·46막힘·59미완·원문105 보존|전체 원장은 미마감|
|checkpoints.tsv|필요|새 연구 snapshot49조각 별도 목록 연결|사용자 파일 삭제는 미승인|
|공유 검사기/환경|이번에는 수정 안 함|diff0|R58의 추가 구현 승인 제안|
|루트09·정제 세션 원장/코드·공유flag|제외|소유 변경0·staging제외|현재 명시 범위 밖|

'''
    text=text.replace('## 4. 검증과 미해결 검사',addition+'---'+chr(10)*2+'## 4. 검증과 미해결 검사',1)
    unresolved='''### 4.3 미해결 검사의 운영 결정

| 검사 | 정확한 대상 | 증거와 상태 | 운영 영향 | 권장 조치 | 대안 | 승인 주체 |
|---|---|---|---|---|---|---|
|전수 정적|현재 소스와 명시 소유 입력|미해결: 마지막69/2/6·HF개별회복0|현재 전체 PASS 주장 금지|공유 collector/read guard A 승인 후 재실행|B별도 복사본/C개별검사만 유지|사용자 R58 구현 승인|
|전체 smoke|run_smoke_check.sh 정본과 Codex 격리 등가 경로|NOT_RUN_PENDING|옛106행동을 새 source 증거로 쓰지 않음|같은 판정·모델팔 유지한 A 경계 회귀 후 실제 시행|현재 부분 증거·보류 유지|사용자 collector 승인·유효 CPU/GPU 시간|
|KoBEST5|공식 task/metric과 평가 전용 환경|BLOCKED 추가5의존성 부재|모델점수 미보고|최소 추가 설치 승인·wheel/metric 검증|독립 새 환경 또는 설치 보류|사용자 설치 승인|
|실제 학습효과|P107 승인 원천·생산 CLI·본학습|미해결·지능효과 미측정|기본 정책/교사를 자동 채택하지 않음|정제 완료·명시 문서 계약 후 본실험|현재 기술 근거만 보존|사용자/원천 소유 세션|

| 정본 스모크 | 현재 처리 | 이유 | 후속 |
|---|---|---|---|
| run_smoke_check.sh | NOT_RUN_PENDING | 넓은 collector·금지 환경 치환·source freshness를 승인된 방식으로 닫아야 함 | 사용자 정본 직접 실행을 지금 요청하지 않고 Codex 동등 경로를 준비 |

'''
    text=text.replace('## 5. 확보한 수치',unresolved+'---'+chr(10)*2+'## 5. 확보한 수치',1)
    text=text.replace('완료 SH7·합성66·새연구 snapshot1','완료 -done SH7·합성66·새연구 snapshot1',1)
    text=text.replace('|실행|8h 교사 재개 SH','|실행|run_smoke_check.sh 사용자 정본·Codex 격리 등가|현재 source 전체 smoke NOT_RUN_PENDING|지금 직접 실행을 요청하지 않음. 우선 A범위 승인 여부 결정|승인·경계 회귀·유효 실행 시간|같은 모델팔과 판정의 새 전체 smoke|'+chr(10)+'|실행|8h 교사 재개 SH',1)
    fence=chr(96)*3
    body='''### 제목

'''+fence+'''text
문서: 오후 연구 검산과 최종 인계를 마감한다
'''+fence+'''

### 본문

'''+fence+'''text
한국어 로컬 커밋의 실제 경로·bytes와50원로그 폐합을 확인한다.
원장51·105 완료와59 잔여·46 의존성 막힘을 구분한다.
최초 인계 원문105건을 보존하며 오후 결과와 다음 승인 선결을 반영한다.
현재 전체 smoke 미실행·검사 간접 판독 사고·타 세션 제외를 명시한다.
'''+fence+'''

연구 코드·원로그397경로의 실제 커밋은3268dce7이다. 이 최종 인계/원장 검산을 작은 후속 로컬 커밋으로 남기며 push/PR은 하지 않는다.
'''
    text,count=re.subn(r'(?ms)^## 8\. .*?(?=^## 9\.)',lambda _: '## 8. 커밋 메시지'+chr(10)*2+body+chr(10)+'---'+chr(10)*2,text)
    assert count==1
    text=text.replace('## 10. 세션 시작 프롬프트','## 10. 세션 시작 프롬프트'+chr(10)*2+'- **열린 WIP 상태**: 있음.',1)
    text=text.replace('- **현재 금지**:','- **승인 전 금지**:',1)
    text=text.replace('- **첫 확인**:','- **첫 행동과 선결**:',1)
    TARGET.write_text(text)
    with receipt.open('x',encoding='utf-8') as stream:
        json.dump(dict(schema='AFTERNOON_HANDOFF_CONTRACT_V3',
            original_handoff_update='HANDOFF_UPDATE_v2.json',failed_structure_log='HANDOFF_STRUCTURE_v2.log',
            failed_structure_errors=9,failed_text_snapshot=str(snapshot.relative_to(ROOT)),
            before_sha256=hashlib.sha256(before.encode()).hexdigest().upper(),
            after_sha256=hashlib.sha256(text.encode()).hexdigest().upper(),
            shared_checker_changes=0,model_or_gpu_runs=0,original_directive_rows_unchanged=True),stream,indent=2)
    print('handoff canonical columns, smoke disposition, copyable messages and start fields restored')


if __name__=='__main__':main()
