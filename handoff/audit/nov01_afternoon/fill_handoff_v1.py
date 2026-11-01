"""Write only the new handoff and commit receipt; the WIP is read-only here."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'handoff/202611011123_HANDOFF.md'
BASE = Path(__file__).parent
WIP = ROOT / 'handoff/WIP_20261022_작업원장.md'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()

def main():
    old = (ROOT / 'handoff/202610271445_HANDOFF.md').read_text()
    wip_before = WIP.read_bytes()
    rows = []
    for line in wip_before.decode().splitlines():
        if line.startswith('| **') and len(line.split(' | ')) == 6:
            c = line.split(' | ')
            rows.append([c[0].removeprefix('| **').removesuffix('**'), *c[1:5], c[5].removesuffix(' |')])
    assert len(rows) == 105
    purpose = {}
    for line in old.splitlines():
        if re.match(r'^\| [0-9]+[A-Z]? \|', line):
            c = line.split(' | ')
            if len(c) >= 6:
                purpose[c[0][2:]] = c[2]
    purpose.update({'101':'소유 모델을 보존하며 정리 후보와 실제 공간 단위를 검증', '102':'허가한 합성만 삭제하고 연구모델·원로그를 보존', '103':'격리 합성 정리기의 안전한 기본 미리보기와 검증 제공', '104':'정제 외 미완 연구와 공식 평가를 이전11시·8GB 경계에서 진행', '105':'소유 커밋·신규 인계 후15시까지 미완 연구 재개'})
    table = ['| # | 사용자가 지시한 것 | AI 가 판단한 목적 | 그래서 필요했던 작업 | 실제로 한 것 | 결과 |', '|---|---|---|---|---|---|']
    for n, directive, status, work, artifact, resume in rows:
        need = resume if resume != '—' else '원지시별 실제 처리·원로그·산출물과 한계 대조'
        table.append('| ' + ' | '.join([n,directive,purpose.get(n,'원지시의 범위·실제 수행·미완과 증거 보존'),need,work,status+' — '+artifact])+' |')
    commit = git('rev-parse','HEAD').strip()
    scope = json.loads((BASE/'COMMIT_SCOPE_v1.json').read_text())
    expected = set((BASE/'STAGE_ALLOWLIST_v1.paths').read_bytes().decode().split(chr(0))[:-1])
    expected.update(['handoff/audit/nov01_afternoon/INDEX_CHECK_v1.json','handoff/audit/nov01_afternoon/COMMIT_MESSAGE_v1.txt'])
    actual = git('diff-tree','--no-commit-id','--name-only','-r','-z',commit).split(chr(0))[:-1]
    assert set(actual) == expected
    assert git('diff','--cached','--name-only','-z') == ''
    assert hashlib.sha256((ROOT/'scripts/flag_whitelist.tsv').read_bytes()).hexdigest().upper() == scope['foreign_flag_sha256']
    receipt = dict(schema='NOV01_OWN_COMMIT_RECEIPT_V1', commit=commit, parent=scope['head'], paths=len(actual), exact_paths_match=True, raw_logs=45, smoke_logs=1, per_item_raw_local=913, per_item_raw_bytes=680782247, foreign_staged=0, foreign_flag_unchanged=True, index_empty=True, push_pr=0)
    (BASE/'COMMIT_RECEIPT_v1.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+chr(10))
    text = OUT.read_text()
    text = text.replace('- **정적 감사 기록**: (WIP close 전에 생성한 `audit/*_STATIC_AUDIT.json` 링크로 교체)', '- **정적 감사 기록**: [최종 소유 감사](audit/nov01_independent/FINAL_CLOSED_SCOPE_STATIC_20261101T1054_v1.json), 534입력71PASS/0ERROR/6NOT_RUN. 신규 WIP105·인계는 이 옛 감사의 동일 바이트라고 주장하지 않는다.\n- **정확 열린 원장**: [WIP_20261022_작업원장.md](WIP_20261022_작업원장.md), 세션01a0b33b-d14e-7c40-ada8-229a1f97eabd, 105건.\n- **현재 허가**: 기본 GPU 사용자 실행 원칙에 대해 사용자105가 2026-11-01 15:00 KST까지 CPU/GPU와 소유 staging·로컬 commit을 명시 위임했다. 사용자 VRAM 상한은 없고 물리 여유·단일GPU·마감종료는 유지한다.\n- **원로그 폐합**: [45원로그 manifest](audit/nov01_independent/RESULT_CLOSURE_v5.json), 재검사 오류0.\n- **실제 커밋**: '+commit+' · [영수증](audit/nov01_afternoon/COMMIT_RECEIPT_v1.json).\n- **스냅샷 범위**: 소유 커밋 뒤 오후 연구 전 인계다. 이후 진행은 정확 열린 WIP가 소유한다.')
    def section(number, title, body):
        nonlocal text
        pattern = r'(?ms)^## '+re.escape(number)+r'\. .*?(?=^## |\Z)'
        text, count = re.subn(pattern, lambda m:'## '+number+'. '+title+chr(10)*2+body.strip()+chr(10)*2+'---'+chr(10)*2, text)
        assert count == 1, (number,count)
    section('0','사용자 지시 105건 — 원문과 처리', '원장의 과거 완료·현재 미완을 그대로 보존한다. 사용자105의 소유 커밋은 완료했고 신규 인계 검증·오후 연구는 진행 중이다.'+chr(10)*2+chr(10).join(table))
    section('1','가장 중요한 것 세 가지', '''1. 소유2,117경로를 한국어 로컬 커밋했다. 원로그45·스모크1과 실패/보류 원형을 포함하며 타 세션 정제와 flag 변경은 제외했다. 문항별 원답·우도·길이913개680,782,247B는 원위치와 SHA 목록으로 보존하고 Git에는 넣지 않았다. 커밋 파일20MB 초과0이다.
2. 새 지능 향상은 관측하지 않았다. Tiny MMLU는 약23~25%, Falcon0-shot은32.3885%이고 실제 대화의 반복·질문 재출력·무관답이 남는다. 합성30업데이트의 기술 성공을 본학습/지능 개선으로 승격하지 않는다.
3. 새 마감은11월1일15시다. 원장51 Falcon5-shot의 새 차등/비용/전량을 우선하고59 제품 학습 통계 연결,46 최소 의존성 검토를 잇는다. 타 세션 정제·정제 전 추가300M·보호TinyDataset·설치/미승인취득·실제 삭제·push/PR는 제외한다.''')
    section('2','무엇을 했나', '''### 2.0 사용자용 판독

| 관측 | 의미 | 사용자 영향 | 다음 행동 |
|---|---|---|---|
| Tiny MMLU0은23.0024/23.1733%,5는25.3454/25.4166%, Falcon0은32.3885% | Tiny는 비교 모델의 분별 수준에 미달 | 일반 지능 개선을 주장할 근거가 없다 | Falcon5를 같은 공식 방식으로 완료 |
| 독립한영200질문에서 Native0/200·Broad10/200 사용가능 | 종료·형식과 질문 이해가 다름 | 반복·무관답·질문 재출력이 남음 | 정제 후 본학습에서 실답 재검증 |
| 합성24갱신 uniform10.164/통계10.404/적응10.276초 | 이번 조건의 통계 비용은 작으나 학습 효과는 모름 | 기본 정책 자동 채택 불가 | 제품CLI·전체 재개 연결 |
| 긴 이력15점 로짓/argmax 동일·일부 V 엄격비교 음성 | 작은 차이가 반복의 유일 원인이라는 증거는 없음 | 캐시 수정만으로 회복을 약속하지 않음 | 원음성8·상대오차 함께 보존 |
| 소유2,117경로 커밋·913raw 로컬SHA | 기록 보존과 대용량 원형을 분리 | 타 세션 정제는 커밋에 없음 | 신규 인계 검증 후 별도 커밋 |

### 2.1 목적·방법·결과와 한계

[육하원칙 전체 안내](../docs/research/20261101_정제외_독립연구_결과안내.md)와 결과101 §§563~577, 결과107 §§10~14가 상세 정본이다.
P107은 부모 복사본·합성 causal8+MNTP8·micro8×accum16×1024·BF16 AMP/FP32 master·Muon RMS4+AdamW였다. 비용24+재개6=30갱신, 실제 문서 학습0·지속 연구CP 저장0이다. 메모리 재개 model/optimizer/policy/source/RNG/loss exact였으나 disk/scheduler/제품CLI는 미완이다.
MMLU는 고정 공식57과제·0/5-shot 별도·4선택지 전체우도 합·14,042 가중집계, FP32/MATH/TF32off/batch4/context1024다. tokenizer/사전학습/구조는 다르다. Falcon0은 공식 HFLM 문맥 로짓 재사용ON, Tiny는OFF, 모델KV는OFF다. 114문항/456우도 정합 후15.840→4.273초를 관측하고 전량을 완료했다. 이는 채점 최적화이며 학습 가속/지능 개선이 아니다.

### 2.2 음성 이유와 실제 답 확인

Tiny 네 MMLU 조건은 과제별 정답분포를 보존한2,000순열에서 뚜렷한 분별 근거를 확인하지 못했다. Falcon0 상방 꼬리0.00049975는 유한 재표집의 분해능이며 일반지능 확률이 아니다. 후행 최빈D26.890756%는 사전 학습 분류기가 아니다.
GSM8K strict/flexible 적중은 Native0/16·Broad0/22, 각1,319문항이다. 숫자 적중38+각 첫 오답8=54표시답을 읽었고 인물·단위·비율 오류를 구분했다. 독립한영400답도 전부 읽었으며 Broad10건은 KO5/EN5, 일상질문 KO1/20·EN0/20이다. 공식 점수는 정정 학습에 재사용하지 않았다. 역사 사전학습 오염은 미확인이다. 예시 잘림·실제질문 잘림은 별도 전수 검산했고 긴 문맥 공개평가 동등성을 주장하지 않는다.

### 2.3 사고와 정정

초기 정적 수집기가 상대 감사문서를 간접 읽은 접근을 공개·정정했고 후속 수집을 소유 명시 inventory로 제한했다. 상대 정제 원문·코드·캐시·프로세스의 조작은0이다. 언어 초안 차단, 잘못된 profile 목적, 이름 충돌, CPU timeout, 봉인패킷 복구는 원형/원실패를 보존했다. 신규 인계 작성 첫 inline 명령도 WIP 읽기와 다른 파일 쓰기를 혼합해 직접수정 guard가 실행 전에 거부했다. 실제 WIP 쓰기0·부분 산출물0이며, 쓰기 경로가 명확한 이 전용 helper로 분리했다. guard를 끄거나 WIP를 직접 편집하지 않았다.''')
    section('3','무엇이 바뀌었나 — 코드·도구', '''P107 opt-in 실제 갱신 어댑터·공식 평가/검산·NVML 조회·긴KV CPU 비교·격리 합성 정리기·소유 정적 수집·정확 경로 시각검사를 반영했다. 정리기 실제 삭제는0이다. 큰 원답은 기존 위치를 이동하지 않고 해당 가족 JSONL만 ignore했으며 SHA/소형판정/원로그를 Git에 남겼다.

### 3.1 정본 동기화·미갱신 사유

| 산출물 | 필요 여부 | 실제 diff | 미갱신 사유 |
|---|---|---|---|
| 결과101/107·실험목록 | 필요 | 실제 완료·음성·원로그 연결 커밋 | 없음 |
| 계획P106B/P107·계획목록 | 필요 | 실제 완료와 미완 구분 | 없음 |
| 기준표/METHODS/방법론03·05/COMPASS | 필요 | 기술·품질·미완 분리 | 없음 |
| experiments.tsv·SH | 필요 | done/hold·명령SHA 보존 | 없음 |
| checkpoints.tsv·격리 정리기 | 필요 | 합성66 목록·정리기 구현 커밋 | 실제 삭제 미승인·미수행 |
| scripts/flag_whitelist.tsv | 제외 | 이번 커밋0 | 타 세션 소유 |
| Codex01/02/08 | 필요 | 계측·시각·사고 기록 커밋 | 없음 |
| 보호자료·정제캐시·루트09 | 불필요 | 변경0 | 현재 소유 범위 밖 |
| 신규 인계·WIP105 | 필요 | 이 파일·정상 writer 기록 | 오후 연구는 진행 중 |''')
    section('4','조심할 것 — 다음 세션이 밟을 자리', '''### 4.1 스모크·동적 검증 계승

| 항목 | 상태 | 근거 | 사용자 요청 반영 |
|---|---|---|---|
| run_smoke_check.bat / run_smoke_check.sh | NOT_REQUIRED(커밋·인계는 새 모델 소스 변경이 없고 기존106행동 실제0 뒤 추가CPU 도구는 해당 회귀로 검증했다) | 현재 모든 파일의 새스모크 PASS로 확대하지 않는다 | 요청 없음. 새 제품 경로 변경 뒤 총괄이 위임 창 안에서 별도 시행 |

### 4.2 미해결 검사·판정

| 검사 | 정확한 대상 | 증거와 상태 | 운영 영향 | 권장 조치 | 대안 | 승인 주체 |
|---|---|---|---|---|---|---|
| 제한 정적6종 | heldout/evalpool/full registry/legacy handoff/plot/tag archive | 원감사 NOT_RUN 사유 보존 | 전체 범위 증명 아님 | 소유 경계별 후속 확인 | 명시 소유 범위 사용 | 사용자·소유 세션 |
| Falcon5 | 새 shot별 parity/profile/영수증 | NOT_RUN | 외부5shot 미완 | 새 비용·차등 후 전량 | 현재0 비교 유지 | 사용자105 위임 총괄 |
| KoBEST5 | metric 의존성 | 원본4561·CPU15 완료, 모델미실행 | 한국어5과제 미평가 | 기존환경 재사용·최소 설치 검토 | 미승인 설치 없이 진행 | 설치는 사용자 |
| P107 제품 | CLI/causalKD/disk/scheduler/loader | 합성비용·메모리재개만 확인 | adaptive 본학습 미준비 | 기본off 연결·전체 재개 | uniform 유지 | 사용자105 위임 총괄 |''')
    section('5','확보한 수치', '''| 항목 | 조건·수치 | 판정 |
|---|---|---|
| Tiny MMLU0/5 | Native23.002421/25.345392%, Broad23.173337/25.416607%, 각14042 | 새 측정·지능 개선 아님 |
| Falcon0 |4548/14042=32.388549%|고정0shot 분별 근거|
| GSM8K strict/flexible |Native0/16·Broad0/22, 각1319|숫자 적중과 풀이 정답 분리|
| P10724비용갱신 |uniform10.16382193/관측10.40444386/적응10.27583707초|한 조건 중앙값|
| P1076재개갱신 |메모리781346521B·전체관련상태 exact|disk/제품 미완|
| 최종 소유정적 |534입력71PASS/0ERROR/6NOT_RUN|STATIC_ONLY|
| 원로그 폐합 |45건·재검사0|과학적 판정 보증 아님|
| 커밋 |2117경로·45원로그·1스모크·913raw 로컬SHA|타세션 제외·push/PR0|''')
    section('6','열린 질문', '''Falcon5의 문맥 재사용이 OFF와 같고15시까지 전량을 닫을 수 있는가? P107 실제 언어·숫자·희귀 선택편향과 전체 재개는 미완이다. 정제 완료·편입은 다른 세션 소유이며 공개 수치를 학습 허가로 승격하지 않는다.''')
    section('7','다음 권장 실험 순서 — 역사 예산8.0h·현재 즉시 실행0', '''| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 인벤토리 | 실행상태 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|---|---|
|1|3|P106B 사용자8h 교사 증분생산|run_P106B_Stage4fsXW_user_supported_resume8h.sh|8.0|8.0|PRESENT|HOLD|원천/cursor·생산계약 검증과 새8h창|현재15시창 및 정제 소유 경계 밖이므로 자동 실행하지 않음|

**시간 미달 사유**: 현재 위임 창은15시까지 약3.5시간이고 이8h의 원천 선결은 닫히지 않았다. 완료 런을48h에 맞추려고 재실행하지 않는다. 원장51 Falcon5는 새 shot별 차등/비용/profile 구현 전이므로 계획에만 두고 아직 배치를 만들지 않았다.59·46도 위4.2 선결을 따른다.

> FRONTIER_COVERAGE_NOT_VERIFIED — 이번 인계로 열린 원장을 닫지 않는다. 새 실행 큐가 확정되면 별도 전수 갱신한다.
> FRONTIER_SEMANTIC_NOT_VERIFIED — 과거 동일 소스 전제와 과거HOLD를 새 수작업 판정으로 오인하지 않는다.

### 7.1 이전 큐 제외·완료 이관

| 이전 배치 | 처리 | 근거 |
|---|---|---|
|run_P106B_Stage4fsXW_user_supported_resume8h.sh|본표 HOLD 유지|원천·새8h창 선결 재감사|
|P013/P107 과거 기술SH|완료 이관·원형 보존|직전 실제 비용/재개와 명령SHA|
|Tiny MMLU4/GSM2·Falcon0 SH|완료 이관·-done|전량·독립root0·명령SHA|
|원 Falcon0/5 full hold SH|과거 HOLD 유지|만료profile을 현재 허가로 조용히 해제하지 않음|''')
    section('6b','사용자에게 부탁하는 것', '''| 대상 | 정확한 위치 | 근거 | 사용자가 할 행동 | 완료 신호 | AI 후속 처리 |
|---|---|---|---|---|---|
|실행|오후 소유 연구|사용자105가15시까지 총괄에 위임|이번에는 요청할 것이 없다|총괄이 실제 종료·결과 보고|원장51·59·46 우선 진행|
|삭제|완료 -done SH·합성66|재현 명령·재실행 계획을 개별 대조해야 하며 현재 실제 삭제 미승인|이번에 확정한 삭제 가능한 -done 배치 없음. 현재 원형 보존|별도 대상 확정·승인 시만 삭제|목록/명령 보존·실제 삭제0|
|그 외|KoBEST 의존성|추가 설치 미승인|지금 회신할 것은 없다. 재사용 불가 시 정확 패키지/버전 후속 제안|별도 설치 허가|미승인 설치 없이 다른 작업|''')
    section('8','커밋 메시지', '''### 제목

```text
실험: 적응형 학습 연결과 공식 평가 원로그를 보존한다
```

### 본문

```text
- P107 실제 갱신 비용·메모리 재개와 전체 스모크106행동 근거를 기록한다.
- TinyLM MMLU 네 조건·GSM8K 두 조건과 Falcon0 전량·실패·보류·원답 판독을 보존한다.
- VRAM 조회·독립검산·정확 시각 경로 오류와 관련 회귀를 검증한다.
- 격리 정리기를 추가하되 실제 삭제는 하지 않는다.
- 큰 문항별 원본은 로컬/SHA로 보존하고 타 세션 정제 변경을 제외한다.
```

실제 커밋은 머리말 영수증이 소유한다. 이 신규 인계와 이후 연구는 별도 후속 커밋이다.''')
    section('9','compact 프롬프트', '''M4·M5 E2E PASS 전의 수동 보조이며 자동 소비 계약이 아니다.

```text
정확 WIP는 handoff/WIP_20261022_작업원장.md·105건·동일세션01a0b33b-d14e-7c40-ada8-229a1f97eabd다.
사용자105 새허가는11월1일15시까지 CPU/GPU 사용자VRAM상한없음·소유staging/로컬commit이다.
소유2117경로 e6c1a40b·원로그45·스모크1·913문항raw 로컬/SHA 보존. 새인계는 후속 검증/커밋한다.
타세션정제 private/코드/캐시/프로세스·flag·TinyDataset·정제전추가300M·설치/미승인취득·삭제·push/PR 제외.
TinyMMLU4/GSM2/Falcon0 full은 끝났다. 새 지능학습 성과 없고 반복/무관답은 남는다.
다음은51 Falcon5 새shot별차등/비용/profile/전량,59 제품통계,46 의존성 재사용 검토다.
15시 전 소유 GPU/큰CPU 종료·원로그/실패·명령SHA·원장/인계/정적/로컬commit 마감.
```''')
    section('10','세션 시작 프롬프트', '''- **열린 WIP 상태**: 있음.
- **정확한 WIP / 첫 미완료**: handoff/WIP_20261022_작업원장.md /1번은 다른 세션 정제로 이번 접근 제외. 현재 범위 첫 행동105·51번.
- **첫 행동과 선결**: 신규 인계의 실제 검사/커밋을 확인하고 Falcon5의 새 차등·비용·마감 여유를 검증한다. 완료 Tiny4/Falcon0 재실행 금지.
- **승인 전 금지**:15시 이후 새연구, 정제 편입·추가300M·무승인 설치/취득·실제삭제·push/PR 금지.''')
    section('11','참조 치트시트', '''| 정본 | 위치 |
|---|---|
|진행·권한|handoff/WIP_20261022_작업원장.md|
|실제수치·원답|결과101 §§563~577·결과107 §§10~14|
|육하원칙 안내|docs/research/20261101_정제외_독립연구_결과안내.md|
|기술·평가 감사|handoff/audit/nov01_independent/|
|현재 커밋·raw SHA|handoff/audit/nov01_afternoon/|
|공개 조정|tmp/COORD_EXPERIMENT_01a0b33b.md·상대는 공개 COORD_HOLD만 읽기|''')
    OUT.write_text(text,encoding='utf-8')
    assert WIP.read_bytes() == wip_before
    print(json.dumps(dict(handoff=str(OUT.relative_to(ROOT)), bytes=OUT.stat().st_size, directive_rows=len(rows), wip_unchanged=True, commit=commit),ensure_ascii=False))

if __name__ == '__main__':
    main()
