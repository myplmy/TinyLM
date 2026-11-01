"""Update this session's already-created handoff; the WIP is read-only here."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).parent
HANDOFF=ROOT/'handoff/202611011123_HANDOFF.md'
WIP=ROOT/'handoff/WIP_20261022_작업원장.md'


def main():
    assert not (BASE/'HANDOFF_UPDATE_v2.json').exists(),'one-shot writer; preserve final handoff'
    before=HANDOFF.read_text();wip_before=WIP.read_bytes()
    rows=[]
    for line in wip_before.decode().splitlines():
        if line.startswith('| **') and len(line.split(' | '))==6:
            c=line.split(' | ')
            rows.append([c[0].removeprefix('| **').removesuffix('**'),*c[1:5],c[5].removesuffix(' |')])
    assert len(rows)==105 and len({r[0] for r in rows})==105
    old={}
    for line in before.splitlines():
        if re.match(r'^\| [0-9]+ \|',line):
            c=line.split(' | ')
            if len(c)==6:old[c[0][2:]]=c
    assert len(old)==105
    table=['| # | 사용자가 지시한 것 | AI 가 판단한 목적 | 그래서 필요했던 작업 | 실제로 한 것 | 결과 |',
           '|---|---|---|---|---|---|']
    for n,directive,status,work,artifact,resume in rows:
        assert old[n][1]==directive,(n,'original directive changed')
        need=resume if resume!='—' else '원지시별 실제 수행·원로그·산출물과 한계를 대조했다'
        table.append('| '+' | '.join([n,directive,old[n][2],need,work,status+' — '+artifact])+' |')
    now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    commit=json.loads((BASE/'COMMIT_RECEIPT_v2.json').read_text())['commit']
    header='''# HANDOFF 2026-11-01 11:23 — 오후 독립 연구와 소유 커밋의 최종 인계

- **이전**: [202610271445_HANDOFF.md](202610271445_HANDOFF.md).
- **코드가 정본**: tinylm 구현과 실제 원로그가 수치·행동을 소유한다.
- **기본 실행 경계**: GPU는 사용자 실행 원칙이며 사용자105가11월1일15시까지 직접 실행을 위임했다. 그 뒤에는 새 권한을 확인한다.
- **최종 갱신**: '''+now+'''. 최초11:23 스냅샷은2928507b에 보존했다. 같은 파일의 오후 결과 갱신이며 최초 존재 시각을 새로 꾸미지 않는다.
- **정적 감사 기록**: [정적 감사 기록](audit/nov01_afternoon/PRODUCT_BOUNDARY_STATIC_AUDIT.json), 실제69PASS/2ERROR/6NOT_RUN인 중간 실행이다. HF import 경로는 후속 개별0으로 회복했으나 전수는 다시 돌리지 않았다. 이 감사가 현재 소스 전체 PASS라는 주장은 하지 않는다.
- **환경 증거 상태**: STATIC_ONLY / E2E_NOT_RUN. 실제 완료한 모델 평가·기술 GPU 결과와 환경 종합검증은 별개다.
- **현재 전체 smoke**: NOT_RUN. 옛106행동 성공은 보존하지만 현재 변경 소스의 전체 성공이나 타 세션 간접 판독0으로 재사용하지 않는다.
- **정확 열린 원장**: [WIP_20261022_작업원장.md](WIP_20261022_작업원장.md), 세션01a0b33b-d14e-7c40-ada8-229a1f97eabd, 105건. 51·105는 완료, 전체 원장은 미완이다.
- **원로그 폐합**: [50원로그 manifest](audit/nov01_afternoon/RESULT_CLOSURE_v1.json), 오류0. 평가와 실패 원로그·과거 음성을 보존한다.
- **실제 커밋**: e6c1a40b(2117경로)·2928507b(첫 인계/검산)·'''+commit+'''(오후397경로). [오후 영수증](audit/nov01_afternoon/COMMIT_RECEIPT_v2.json).
- **보호 경계**: 정제 전 추가300M·보호TinyDataset·다른 세션 전용 원천/새캐시/원장/코드 변경·설치·삭제·push/PR는 수행하지 않는다. 이 문서가 향후 실행 허가를 새로 만들지 않는다.

---

'''
    text=header+before[before.index('## 0.'):]
    def section(label,title,body):
        nonlocal text
        pattern=r'(?ms)^## '+re.escape(label)+r'\. .*?(?=^## |\Z)'
        text,count=re.subn(pattern,lambda m:'## '+label+'. '+title+chr(10)*2+body.strip()+chr(10)*2+'---'+chr(10)*2,text)
        assert count==1,(label,count)
    section('0','사용자 지시 105건 — 원문과 처리',
        '원문105건과 과거 완료를 보존했다. 오후 현재 상태는 원장과 대조했고 타 세션 정제의 미완을 임의 마감하지 않는다.'+chr(10)*2+chr(10).join(table))
    section('1','가장 중요한 것 세 가지','''1. 소유 누락과 원로그를 검산해 한국어 로컬 커밋3개를 완료했다. 오후397경로는 exact allowlist/bytes·50결과원로그+기존smoke1의 index 일치를 확인했다. 타 세션 정제와 공유 flag는 커밋에서 제외했다. 대량 원답 JSONL·가중치는 로컬에 보존한다.
2. 원장51은 Native/Broad/Falcon 각0/5shot의 여섯 MMLU14,042전량·독립root·과제별2000순열까지 완료했다. Tiny는약23~25%·Falcon은32.39/34.00%다. 새 Tiny 지능/일상대화 개선은 확인하지 못했고 반복·질문 재출력·무관 답변 한계는 유지한다.
3. 원장59는 명시 문서/스케줄/디스크6회·causal-only KL16회·새 프로세스2회 합성 기술 시험을 완료했다. 전체 상태 재개 exact·기본None exact·교사 동결이며 KL 비용은+33.34%였다. 실제 원천 편향·생산 CLI·본학습 품질은 미완, 정제 전 추가300M은 금지다.''')
    section('2','무엇을 했나','''### 2.0 목적·방법·실제 결과

| 작업 | 목적·방법 | 실제 결과 | 한계·다음 행동 |
|---|---|---|---|
| Falcon5 MMLU | 같은 공식 요청·1024·batch4·FP32/MATH, 비용456우도 parity 뒤 전량 | 40825/0·독립44545/0, 4774/14042 | 긴 문맥 leaderboard와 구분 |
| 여섯 조건 비교 | 기존 Tiny4/Falcon0은 재실행하지 않고 같은2000순열/대응 문항 집계 | 7752/0, Tiny 네 조건p0.18~0.69·Falcon각1/2001 | 다른 사전학습/어휘/구조 차이·과거 오염 미확인 |
| P107 문서/디스크 | 명시 합성4문서·기존 배치와 cosine/warmup, 새 source/optimizer/session 재개 | 69640/0·root76538/0, 전체 상태 exact | 새 snapshot1개49조각, 실제 원천 품질0 |
| P107 교사 KL | causal CE+0.1KL만 추가, masked CE 유지, None/KL/KL/None | 10664/0·root24560/0, 교사 불변·반복 경로 exact | Native 동어휘 기술 교사이며 지식 향상 시험 아님 |
| 새 프로세스 | 기존 snapshot 읽기 전용, 새 worker의2회와 옛 계속 경로 대조 | 84306/0·root86955/0, 전체 상태 exact·새저장0 | 정전/전원 손실 시험은 아님 |
| 누락 보존 | 옛 완료SH2·NVML 실패보고서 추가, 낡은 preview는 로컬 보존 | 신규5원로그 포함50폐합0,397경로 커밋 | 타 세션 파일 목록 전량도 Git에 남기지 않음 |

### 2.1 코드·검증 범위

제품 내부 opt-in은 document_source/hybrid_session/boundary_store/causal_teacher와 adaptive_training의 None 기본 보존이다. 기존 _kd_kl·LR식을 재사용했다. source 파일·교사/토크나이저 SHA·경계 상태를 고정하고 교사 parameter/storage 공유·미래보기 mask·다른 schema/교사/계수를 거부한다. 기존 None과 옛 모듈의4회 전체 상태는 exact였다.

관련 CPU40과 새 프로세스 CPU39는 각각 실제0이며 공유 사례를 합쳐79개 고유 시험으로 세지 않는다. 첫 통합51에는 기존11개가 중복 수집돼 수정했다. Python150개 구문과 SH7개 별도 bash 구문은0이었다. 개별 attrs48입력/제외canary 거부와 결함1개 검출은 전체 정적 대체가 아니다.

### 2.2 사용자에게 미치는 영향

지금 모델을 새로 지능이 오른 모델로 배포할 근거는 없다. 실제 대화의 반복·문맥/대상 혼동은 기존 음성으로 보존한다. 현재 도움은 공식 비교 완료와 향후 실제 교과를 안정적으로 잇는 학습·재개·비용 근거다. 상세 설명은 [오후 결과보고](../docs/research/20261101_오후_독립연구_결과보고.md)를 따른다.

### 2.3 다른 세션과의 경계

공개 tmp 조정 메모만 확인하고 다른 세션 정제 코드/원장/원문/새캐시를 수정·staging하지 않았다. 다만 넓은 원형 검사기의 scripts 본문 수집을 놓쳐 간접 판독 경로를 남긴 사고를 확인했다. 정확 open 수는 미확인이다. Codex08·공개 조정 메모·아래4.2에 기록했고 전수/스모크를 다시 실행하지 않았다. 원천 해결은 다른 세션에 맡긴다.''')
    section('3','변경 파일과 정본','''| 영역 | 정본·변경 | 범위 |
|---|---|---|
| 결과 | 결과101§578~579·107§15~17·실험목록 | 원로그·수치·실제 한계 |
| 계획 | P106B14h/i/j·P1075/6/7·실험계획목록 | 결과 회수·완료 상태 |
| 제품 내부 | tinylm/train/document_source.py·hybrid_session.py·boundary_store.py·causal_teacher.py·adaptive_training.py | opt-in만 추가, None 기본 보존 |
| 독립 진단 | scripts/diag_p106b_falcon_logitreuse_shots.py·diag_p107_disk_resume.py·diag_p107_causal_kd_cost.py·diag_p107_process_resume.py와 CPU 회귀 | 독립 프로세스로 실행, 여러 driver를 한 프로세스에 연쇄 import하는 생산 API가 아님 |
| 원형 보존 | audit/nov01_afternoon/closed_gpu_sources_v1·v2와 완료 launcher manifest_v1~v4 | inactive 데이터, 환경 fallback 아님 |
| 지식·방향 | METHODS·03/05·기준표·COMPASS·오후 결과보고 | 수치 정본을 링크 |
| 안전 절차 | Codex08·검사 범위 제안·소유 WIP | 사고·NOT_RUN·추가 승인 |

별도 원장09·환경파일·공유 검사기·정제 전용 코드와 flag는 수정하지 않았다. 오래된 정리 preview2개는 도구 SHA 불일치로 로컬 ignore·원형 보존이며 현재 삭제 계획으로 사용할 수 없다. 새 연구 snapshot은 runs/isolated 아래에만 보존하고 checkpoints.tsv에 별도 목록을 연결했다.''')
    section('4','검증과 미해결 검사','''### 4.1 실제 확인

| 검증 | 실제 상태 | 근거 |
|---|---|---|
| MMLU 전량·공식 인자/샤드·집계 | 여섯 조건 완료, 새 Falcon5/root/순열 모두0 | 101§579·MMLU_EXTERNAL_COMPARISON_v3.json |
| P107 disk/KD/process | 각 GPU/root0·원 부모/소스/교사 불변·최종 ownedCUDA0 | 107§15~17와 세 ACTUAL_ROOT |
| CPU 회귀 | 관련40·새 프로세스39 각각0, 중복 포함 합계 주장0 | P107_KD/PROCESS_CPU_CONTRACT |
| 구문·범위 | Python150/SH7·명시395경로 대조0 | OWNED_SYNTAX/PRECOMMIT_CHECKS |
| 로그 폐합 |50개 오류0 | RESULT_CLOSURE_v1.json |
| Git |397경로 exact·index bytes 일치·raw50+smoke1 exact | INDEX_CHECK_v2/COMMIT_RECEIPT_v2 |

### 4.2 미해결·사고·NOT_RUN

| 항목 | 현재 상태 | 원인과 다음 행동 |
|---|---|---|
| 전수 정적 | 마지막 실제69PASS/2ERROR/6NOT_RUN | HF import는 개별0 회복, 전수 재실행 없음. 합산해 새 전수 PASS를 만들지 않음 |
| 현재 source 전체 smoke | NOT_RUN | 새 source freshness와 넓은 scripts/문서 판독 문제. 원형 기준을 유지하는 A안 승인 후 새 실행 |
| 읽기 범위 | 일부 간접 판독 경로 확인, 정확 수 미확인 | attrs뿐 아니라 call_kwargs/imports/flag_used/whitelist collector도 감사 대상 |
| 개별 attrs 첫 회 | inner0/outer1 원형 보존 | tempfile directory handle까지 guard가 막았음. v2 actual0을 별도로 기록 |
| P107 실교과·제품 | 미완 | source 승인/CLI/언어·숫자·희귀 편향·전체 causal 품질 필요 |
| KoBEST5 | 막힘·모델점수 NOT_RUN | 준비4561/CPU15 이후 추가5의존성 승인 필요 |
| 전체 원장 | 미완 | 51·105만 이번 의미 범위에서 완료, 정제/다른 평가/구조연구 잔여 보존 |

이 문서의 검사는 전체 Codex 환경 종결·새 세션 E2E·모델 지능 향상의 증명이 아니다. 역사 전체 smoke106행동 성공은 보존하며 당시 간접 판독0이라고 주장하지 않는다.''')
    section('5','확보한 수치','''| 항목 | 관측 | 해석 |
|---|---|---|
| MMLU Native0/5 |23.002421/25.345392%|두14042 전량 |
| MMLU Broad0/5 |23.173337/25.416607%|두14042 전량 |
| MMLU Falcon0/5 |32.388549/33.998006%|두14042 전량·공통1024 |
| Falcon5 잘림 |2682문항·10728요청|앞 문맥 절단, 긴문맥 leaderboard와 다름 |
| KL 비용 |9.348611→12.465842초·+33.34%|공통 교사 상주·블록별 첫 회 제외 |
| KL peak reserved |7.013→8.491GB|allocated·저장 크기와 구분 |
| 새 디스크 상태 |781352215B·49조각·각16MB이하|연구 재개1개, Git 가중치 제외 |
| disk save/restore |3.494554/2.174742초|같은 프로세스 세션 복원 |
| 새 프로세스 |2갱신·262144입력 위치·전체 exact|기존 snapshot 읽기 전용·추가저장0 |
| 이전 독립 첫답 |Native0/200·Broad10/200 사용가능|오후 재학습/새대화 개선 판정0 |

원로그 수치와 계산/해석은 결과101·107의 정확 절과 독립 root를 따른다. 합성 오후24갱신을 실제 대화 코퍼스 학습량으로 세지 않는다.''')
    section('6','열린 질문','''정제 완료 전 추가300M은 금지다. 실제 승인된 원천의 문서 경계·언어/희귀/숫자 분포를 어떤 생산 입력 계약으로 넘길지와, causal 생성/우도로 본학습 효과를 확인하는 일이 남는다. 지금 교사 Native는 비용용 동어휘 대조여서 Gemma 지식 이전이나 교사 품질을 대신하지 않는다. 공용 검사 범위 변경은 아래 A안 승인 전 실행하지 않으며 KoBEST 추가 의존성도 미승인이다.''')
    # Keep the exact previous queue row and its inventory/hold state.
    queue=before[before.index('## 7.'):before.index('## 6b.')]
    row=next(x for x in queue.splitlines() if x.startswith('|1|3|'))
    section('7','다음 권장 실험 순서 — 역사 예산8.0h·현재 즉시 실행0','''| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|---|---|
'''+row+'''

**시간 미달 사유**: 사용자105의 이번 창은11월1일15시까지이며 새8시간 실행은 불가능하다. 원천/cursor·생산 계약도 미완이다. 완료한 비교를48시간에 맞춰 다시 실행하지 않는다. Falcon5와 P1075/6/7은 실제 완료 이관했고, 공유 검사 A안·KoBEST는 별도 승인/설치·원천 선결을 닫아야 새 실행을 편성한다. 다음 회차는 승인된 시간과 자료를 먼저 확인한다.

> FRONTIER_COVERAGE_NOT_VERIFIED — 전체 원장을 닫지 않으며 전용 정제 경로를 전역 스캔하지 않는다.
> FRONTIER_SEMANTIC_NOT_VERIFIED — 역사 HOLD·원천 전제의 의미 검증을 생략하지 않는다.

### 7.1 이전 큐 제외·완료 이관

| 이전 배치 | 처리 | 근거 |
|---|---|---|
|run_P106B_Stage4fsXW_user_supported_resume8h.sh|본표 HOLD 유지|원천·새8h창 선결 재감사|
|Tiny MMLU4/GSM2·Falcon0 SH|기존 완료 보존|전량·독립root·명령SHA|
|run_P106B_Stage14iW/14jW 비용/전량 SH|완료 -done·원형 보존|실제29901/40825와root0|
|run_P107_Stage5W/6W/7W SH|완료 -done·원형 보존|실제disk/KL/process와root0|
|옛P107 Stage0W/1W -done SH|누락 staging 회수|이미 끝난metadata/FB 원형·결과107|
|원 Falcon0/5 full hold SH|과거 HOLD 유지|만료 profile을 재사용하지 않음|''')
    section('6b','사용자에게 부탁하는 것','''| 대상 | 정확한 위치 | 근거 | 사용자가 할 행동 | 완료 신호 | AI 후속 처리 |
|---|---|---|---|---|---|
|그 외|[공유 검사 A/B/C 제안](../proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서.md)|Codex00 R58은 작업흐름 생성기/검사기 변경의 직접 지시/승인을 요구|권장 A의 명시 collector/read guard 구현 범위를 승인할지 결정|A 승인 또는 대안 지정|기준·사용자 전역 기본을 보존하고 자식 판독 회귀 후 새 전체 smoke|
|그 외|[KoBEST 의존성 준비](../docs/research/20261101_KoBEST5_공식평가_준비범위.md)|evaluate/sklearn/scipy/joblib/threadpoolctl5개 부재|추가 평가 전용 설치 범위 판단. 지금 설치하지 않음|별도 설치 허가와 버전/closure 검산|공식 task/metric 검증 후 실제모델점수 준비|
|실행|8h 교사 재개 SH|원천/cursor·새 시간창 미완|지금 실행 요청하지 않음|선결과 새 권한 확보|정제 경계를 지키며 새큐 편성|
|삭제|완료 SH7·합성66·새연구 snapshot1|이번 지시의 실제 삭제 승인 없음|이번에 삭제할 것을 요청하지 않음. 현재 보존|별도 정확 대상 승인 시만|원로그/판정·재현 명령과 목록 유지|''')
    section('8','커밋 메시지','''### 제목

문서: 오후 연구 검산과 최종 인계를 마감한다

### 본문

- 한국어 로컬 커밋의 실제 경로·bytes와50원로그 폐합을 확인한다.
- 원장51·105 완료와59 잔여·46 의존성 막힘을 구분한다.
- 최초 인계 원문105건을 보존하며 오후 결과와 다음 승인 선결을 반영한다.
- 현재 전체 smoke NOT_RUN·검사 간접 판독 사고·타 세션 제외를 명시한다.

연구 코드·원로그397경로의 실제 커밋은3268dce7이다. 이 최종 인계/원장 검산을 작은 후속 로컬 커밋으로 남기며 push/PR은 하지 않는다.''')
    section('9','compact 프롬프트','''현재 사용자 지시와AGENTS/Codex 정본을 먼저 읽고 현재시각·권한을 확인한다. 이 인계는2026-11-01 11:23 생성/오후 갱신이며 사용자105의 CPU/GPU 권한은15시까지다. 그 뒤 새실행 허가로 쓰지 않는다.
정확 WIP는 handoff/WIP_20261022_작업원장.md·동일세션01a0b33b-d14e-7c40-ada8-229a1f97eabd·105건이다.51/105완료,46막힘,59생산CLI/실원천편향/본학습효과 미완이며 전체 원장은 열린다.
세모델 MMLU0/5shot 여섯 전량/독립root/순열은101§579에완료. Tiny23~25%·Falcon32~34%이고 새IQ/대화향상0이다. 같은완료비교를다시실행하지않는다.
P107디스크6/KL16/새프로세스2 합성기술갱신은107§15~17에실제완료0. None원형과재개상태exact·교사불변·최종ownedCUDA0·새snapshot1/49조각은보존한다. 실제corpus/품질/제품CLI완료가아니다.
타세션정제전용원장/코드/원천/새캐시/프로세스·보호TinyDataset은열거나고치지않는다. 공개tmp조정만참고하고정제전추가300M/설치/삭제/push는금지다. 공유flag는dirty소유제외다.
공유검사넓은수집에서간접판독사고가있다. 마지막전수69/2/6·HF개별회복0이며현재새전체smoke는NOT_RUN이다. 원형기준/사용자기본유지A안추가승인전공유하네스를바꾸지않는다. 개별CPU/attrs를전수PASS로승격하지않는다.
커밋e6c1a40b/2928507b/3268dce7와소유영수증·50로그폐합이정본이다. 대량JSONL/가중치는로컬SHA로보존하고Git은작은원로그/정본/소스/manifest만쓴다.''')
    section('10','세션 시작 프롬프트','''- **정확한 WIP / 첫 미완료**: handoff/WIP_20261022_작업원장.md. 1/2/8/9 정제는 다른 세션 소유로 제외한다. 현재 범위는59의 승인 원천 계약·제품 입력 선결부터 확인하고46은 설치 승인 전 막힘이다.
- **읽는 순서**: 현재 사용자 지시·AGENTS·CodexREADME/00/06 → 정확 세션 WIP → 동적으로 고른 최신 유효 공유 인계 → COMPASS/기준표 → 해당 스킬.
- **현재 금지**:15시 뒤 실행 권한 추정·정제 전 추가300M·보호자료/타세션 전용경로·설치/삭제/push/PR·공유 검사 무단 변경.
- **첫 확인**: 실제 Git/index·진행 중 소유 프로세스·현재 권한. 완료 MMLU나 합성 재개를 반복하지 않는다. 이 창의 소유 GPU는 모두 종료했다.
- **보고 기준**: 원로그/독립root·공식집계·과학적 해석·품질·STATIC_ONLY/E2E_NOT_RUN을 구분한다. 원장105를 다시 열지 않고 새 요청이면 새행을 추가한다.''')
    section('11','참조 치트시트','''| 목적 | 정본 |
|---|---|
|사용자용 설명|docs/research/20261101_오후_독립연구_결과보고.md|
|공식MMLU|결과101§578~579·MMLU_EXTERNAL_COMPARISON_v3.json|
|학습 연결/재개|결과107§15~17·P107 세 ACTUAL_ROOT|
|소유커밋|audit/nov01_afternoon/COMMIT_RECEIPT_v1/v2.json·INDEX_CHECK_v2.json|
|실행당시소스|closed_gpu_sources_v1/v2·CLOSED_SOURCE_ARCHIVE_v1/v2.json|
|원로그폐합|audit/nov01_afternoon/RESULT_CLOSURE_v1.json·RESULT_RAW_BYTES_v1.json|
|snapshot목록|checkpoints.tsv·P107_DISK_CHECKPOINT_INVENTORY_v1.json|
|검사사고/제안|Codex08·proposal/20261101_정제세션-격리와-공용검사-범위-명시-제안서.md|
|현재작업/방향|정확WIP105건·COMPASS·EXPERIMENT_BASELINES|
|환경규약|AGENTS·ai_dev_tool/Codex/00~08·각 .agents 스킬|''')
    assert WIP.read_bytes()==wip_before,'handoff writer must not modify the WIP'
    HANDOFF.write_text(text,encoding='utf-8')
    record=dict(schema='AFTERNOON_HANDOFF_UPDATE_V2',handoff=str(HANDOFF.relative_to(ROOT)),
        updated_at=now,original_directives=105,all_original_directives_equal=True,wip_unchanged=True,
        previous_text_sha256=hashlib.sha256(before.encode()).hexdigest().upper(),
        final_text_sha256=hashlib.sha256(text.encode()).hexdigest().upper(),
        previous_snapshot_commit='2928507b',research_commit=commit,
        current_full_smoke='NOT_RUN',whole_wip_closed=False)
    with (BASE/'HANDOFF_UPDATE_v2.json').open('x',encoding='utf-8') as stream:json.dump(record,stream,ensure_ascii=False,indent=2)
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
