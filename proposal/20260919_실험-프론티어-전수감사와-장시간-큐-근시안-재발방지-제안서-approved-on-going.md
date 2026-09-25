# 제안 — 실험 프론티어 전수감사와 장시간 큐 근시안 재발 방지

> **작성** 2026-09-19 · **보완** 2026-09-25 · **상태** 🔄승인 후 진행 중 · **분류** 작업방식
> 양식: [`proposal/README.md`](README.md) §3. **아홉 절을 비우지 않는다** — 없으면 *"없다"* 라고 쓴다.
> **승인**: 2026-09-21 사용자 권장 C안 승인. M2 inventory compiler·fixture, M3 당시
> frontier 114/114 + non-DONE disposition 72/72, M4 READY 50.8h + GATED 0.3h 편성까지
> 정적 증거를 확보했다. M5 3회 queue 운영 증거가 남아 완료 이관 전이다.
> **2026-09-25 재발 감사:** COMPASS는 갱신됐지만 새 큐의 현재 frontier 산출물·non-DONE 전수 disposition은 없었다. §6.5~§6.6의 실사와 보완안을 참조한다. 기존 M3/M4는 2026-09-21의 한 번의 편성 증거이지 후속 모든 큐의 자동 보증이 아니다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

직전 큐는 P091~P097 중심의 신규 gate·학습 15개, 실험 합계 13.3h로 편성됐다. 그러나 당시
`test_plan/실험계획목록.md`에는 물리 계획서 113개에 대해 표 행 253개가 있었고, 54개 ID가
중복되어 중복 여분만 137행이었다. P076·P078·P044B·P014D의 첫 행은 실행 전이라고 적었지만
실제 결과 064·066·063·069가 이미 존재했다.

따라서 원인은 단순히 “목록을 안 읽었다”가 아니다. 중복·날짜별 append로 낡은 첫 행과 최신
후속 행이 공존하는 목록에서 최신 신규군만 추려 읽었고, COMPASS·기준표·전체 plan frontier를
한 번에 대조하는 강제 단계가 없었다. 그 결과 오래된 runnable/implementation-ready 질문이
신규 P091~P097 뒤로 밀리고, 48h 기준에 34.7h 못 미치는 큐가 전체 후보를 충분히 감사한 것처럼
보고됐다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

매 큐 편성 전에 모든 계획을 한 행·한 상태로 전수 열거하고, 오래된 진행축과 최신 gate를 같은
준비도·가치·비용 기준으로 비교해 “최신 문서만 본 큐”가 다시 생기지 않게 한다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| 정규화 계획 색인 | `test_plan/실험계획목록.md`의 계획당 1행·3상태 표 |
| 구조 검사 | 중복·누락·강조·소절·상태 중복을 차단하는 정적 checker |
| frontier 감사 | 계획/COMPASS/기준표/launcher를 결합한 준비도·선결·비용 보고 |
| 큐 편성 근거 | 포함·제외한 모든 READY/GATED 후보와 48h 미달·초과 사유 |
| 회귀 fixture | 오래된 runnable 계획이 최신 계획에 가려지면 실패하는 테스트 |

승인 시 다음 큐부터는 “최근 리뷰 문서”가 아니라 전체 frontier가 입력이 되며, 오래된 계획의
누락은 커밋 전 정적 오류로 드러난다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | 0 |
| AI 작업 | ⚙2~4h(감사기·fixture·기존 계획 상태 교정) |
| **사용자가 직접 해야 하는 일** | 최초 frontier 우선순위 표 10~20분 검토 |
| 디스크 | 1 MiB 미만 |

⚙는 추정이며 실측값은 근거와 함께 표시한다.

## 5. 원리·근거

**우리 실측**

| 근거 | 값 | 출처 |
|---|---|---|
| 직전 즉시 큐 | 13.3h, 기본 48h보다 34.7h 부족 | `handoff/202609190726_HANDOFF.md` §7 |
| 구 계획 색인 | 253행·고유 ID 116·중복 ID 54·여분 137행 | 2026-09-19 재구성 전 감사 |
| 물리 계획서 | 113개 | `test_plan/P*.md` |
| WSL preflight 사각지대 | 수정 전 live SH 학습 0건 → 수정 후 학습 4·판정 2건 | `dryrun_batch.py --strict --live-only`; `test_dryrun_shell.py` |
| 대표 누락 | P076 결과064, P078 결과066, P044B 결과063, P014D 결과069가 첫 행에 미반영 | 각 결과문서·계획서 |
| 재구성 후 | 113문서=113행, 상태 중복 0 | `check_experiment_plan_index.py` |
| 2차 의미 감사 | 실행 전 25·진행 47·종결 41; false ongoing 9건 교정 | 결과 050·054·057·058·059·067·071·074 |
| 복구한 오래된 READY | P087 Stage3bW, 기존 checkpoint paired 평가 0.3h | 결과 073 §10.4 |
| 2026-09-20 회수 뒤 | P087 Stage3bW 완료로 실행 전 25·진행 46·종결 42 | 결과 073 §12·계획 색인 |

**외부 근거**: 없다. 저장소 내부 작업흐름과 반복 사고만을 대상으로 한다.

## 6. 방법

| 단계 | 무엇 | 비용 | 다음으로 가는 조건 |
|---|---|---:|---|
| M0 | 계획 색인을 물리 계획서 기준 1행·1상태로 정규화 | 완료 | 문서 수=행 수, duplicate=0 |
| M1 | 상태 checker를 정적 종합검사에 연결 | 완료 | 강조·소절·중복·누락 0 |
| M2 | frontier 감사기를 신설해 각 계획의 READY/GATED/HOLD·첫 선결·비용·최근 실행을 출력하고 BAT·SH preflight를 모두 요구 | **수동 기준선·WSL SH parser 완료** · 자동화 ⚙1.5h | 모든 계획이 한 이유로 분류되고 live 학습 SH 계측이 0이 아님 |
| M3 ✅ 정적 운영 증거 | 114/114 frontier SHA와 non-DONE 72/72 disposition을 현 큐가 소비 | 완료 | `handoff/audit/20260921b_FRONTIER.json`·`20260921b_FRONTIER.md`·`20260921b_FRONTIER_DISPOSITION.md` |
| M4 ✅ 정적 편성 | READY 50.8h를 전부 편성하고 GATED 0.3h는 앞 gate만, 제외 65개 근거 기록 | 완료 | 최대 51.1h; gate 음성 시 후속 자동 승격 금지 |
| M5 | 3회 큐에서 신규/기존 계획 누락률과 사후 재편성 횟수 확인 | 사용자 실행 후 | 누락 0이면 작업방식 승인 완료 |

큐는 시간을 억지로 채우지 않는다. 다만 48h 미달이면 “조건부 본런이 아직 없다” 한 문장으로
끝내지 않고, 계획/진행 표의 모든 후보가 왜 READY가 아닌지 frontier 행으로 남긴다.

### 6.1 frontier 감사기는 무엇인가 — **우선순위 AI가 아니라 전수 inventory compiler**

frontier 감사기는 계획을 스스로 발명하거나 GPU 가치판정을 대신하는 모델이 아니다. 서로 다른
정본에 흩어진 **이미 존재하는 후보를 한 행씩 결합하는 결정론적 스크립트**다.

| 입력 | 감사기가 읽는 것 | 읽지 않는 방식 |
|---|---|---|
| 물리 계획서 | `test_plan/P*.md`의 ID·상단 전체상태·미완 단계·비용·선결·실행이력 | 파일 수정시각만으로 최신 상태 추측 금지 |
| 계획 색인 | 세 표 중 계획당 정확히 한 행인지와 상태 | 색인을 계획서보다 우선하는 정본으로 사용 금지 |
| 결과 정본 | 계획서가 링크한 결과번호·최신 단계의 종료/판정/NOT_RUN | 숫자만 보고 계획 전체 종결 금지 |
| 실행 inventory | `experiments.tsv`, 실물 BAT/SH, `dryrun_batch --strict --live-only` | 없는 launcher 이름 생성 금지 |
| COMPASS | 연구축·현재 반증·우선순위 맥락 | COMPASS 한 줄로 계획 단계 완료 추측 금지 |
| 기준표 | 비교 유효성·태그·자원·판정자 | 기준표의 과거 요약으로 최신 로그 대체 금지 |
| 리뷰 문서 | suffix상 active인 최신 리뷰의 확정/미결 항목과 참조 계획 | absorbed/superseded 초안을 새 지시로 부활시키지 않음 |

출력은 `frontier.json`(기계 정본)과 사람이 읽는 Markdown 표 두 개다. 계획별 최소 필드는
`plan_id`, `plan_path`, `whole_state`, `first_unfinished_stage`, `latest_result`, `evidence_date`,
`launcher_inventory`, `preflight_count`, `readiness`, `first_prerequisite`, `estimated_hours`,
`compass_axis`, `active_review_refs`, `conflicts`, `disposition_required`다.

`readiness`의 권한은 좁다.

- `READY`: 실물 launcher와 구현·선결·preflight가 모두 있다.
- `GATED`: 값싼 앞 gate의 실물 launcher는 있지만 본런은 그 결과에 의존한다.
- `HOLD`: 사람 승인, 미구현 코드, 비교조건 불일치 또는 명시 중단선이 있다.
- `DONE`: 계획 전체 단계가 종결 근거를 가진다. 결과 한 행만 존재한다고 자동 지정하지 않는다.
- `CONFLICT`: 계획·결과·색인·launcher가 서로 다른 상태를 주장해 사람이 먼저 고쳐야 한다.

### 6.2 “GPT에게 직접 전달”의 정확한 뜻

감사기가 Codex 대화창으로 능동 메시지를 보내거나 우선순위를 대신 작성하는 구조는 아니다.
권장 C안은 다음 파이프다.

```text
정본 파일들 → frontier audit(JSON+Markdown+SHA-256) → Codex가 전수 읽음
           → 후보마다 포함/제외/보류 disposition 작성 → handoff checker가 coverage 대조
```

즉 **직접 전달**은 (a) 큐 작성 전에 감사 명령이 성공해야 하고, (b) 그 산출물 경로·hash를 현재
handoff/큐 보고가 참조하며, (c) Codex의 최종 후보표가 모든 `disposition_required` 행을 한 번씩
소비했는지를 checker가 확인한다는 뜻이다. 자동 prompt injection이나 별도 agent 호출은 필요 없다.
감사기가 성공했어도 Codex가 출력을 읽지 않았다면 handoff coverage가 실패한다.

### 6.3 최신 문서만 보는 편향을 막는 원리

핵심은 “오래된 것도 읽어라”라는 문구가 아니라 **집합 보존 invariant**다.

1. 물리 계획 ID 집합 `P`와 frontier 행 ID 집합 `F`가 정확히 같아야 한다(`P = F`).
2. `DONE`이 아닌 모든 행은 현재 큐 본표 또는 `제외·보류 근거` 표에 정확히 한 번 나타나야 한다.
3. 큐가 48h 미달이면 `READY` 미포함 행이 0개여야 한다. 남아 있으면 오류다.
4. 리뷰가 언급한 계획과 COMPASS가 “다음 증거”로 든 계획이 frontier에서 사라지면 오류지만,
   그것만 자동 1순위로 승격하지는 않는다.
5. fixture에는 번호가 오래된 `P014D/P076/P087`과 최신 P09x를 함께 넣고, 최신 N개 파일만
   읽는 구현이면 반드시 coverage가 깨지게 한다.

따라서 파일 날짜·최근 리뷰 순서·번호 크기는 후보 생성의 필터가 아니다. 최신 문서는 우선순위
근거 중 하나일 뿐이고, 전체 집합을 먼저 보존한 뒤 가치·비용·선결을 비교한다.

### 6.4 사람이 정해야 하는 것과 감사기가 정할 수 없는 것

감사기는 launcher 존재, 조건 충돌, 비용, 첫 선결을 기계적으로 보고할 수 있다. 그러나
메모리/품질/속도 중 이번 큐의 목적함수, 과학적 가치, 재승인할 HOLD, 48h 안에서 어느 trade-off를
택할지는 사용자와 Codex의 판단이다. 따라서 M2 출력이 곧 실행 명령은 아니며, M3의 큐 편성은
반드시 각 행의 한 줄 근거와 사용자 승인 경계를 남긴다.

### 6.5 2026-09-25 재발 실사 — 구조 검사와 큐 전수 판단은 달랐다

| 대상 | 직접 확인한 증거 | 판정 |
|---|---|---|
| COMPASS | 커밋 5002db5가 [양자화·토큰/코퍼스·지능/벤치](../handoff/COMPASS.md) 세 행에 P014E·P105·P106을 반영했다 | **갱신 수행**. 이번 누락의 대상이 아니다. |
| 정적 frontier 검사 | [이번 정적 감사](../handoff/audit/WIP_20260925c_STATIC_AUDIT.json)는 frontier_audit·fixture PASS. [정적 묶음](../scripts/check_static_all.py)이 실행한 것은 frontier_audit.py --check | **구조 검사만 수행**. 파일을 보존하거나 현재 큐가 모든 후보를 검토했는지는 보지 않았다. |
| 현 트리 읽기 전용 재계산 | 2026-09-25 현재 물리/색인/frontier **123/123/123**, non-DONE **81**, DONE42·GATED2·HOLD79·READY0·충돌0. 순간 SHA 32F3B569096EE34D9F4D3ED37875C0F4EB983F7331A20E6CD2F45B55AC4A8553 | **현재 집합 정합**. 이 stdout은 보존된 frontier/disposition 산출물이 아니다. |
| 현 큐의 후보별 판단 | [202609250944 handoff §7](../handoff/202609250944_HANDOFF.md)은 실물 2건 0.2h, 시간 미달 사유, 직전 큐 3건의 완료 이관만 기록했다. 현재 frontier SHA와 non-DONE 81개 각각의 포함·제외·보류 행은 없다 | **원 승인 C안의 전수 소비 계약 미수행**. 단, 현재 READY0이므로 0.2h 편성 자체가 잘못됐다는 증거는 아니다. |
| 마지막 보존 frontier | [2026-09-23 R1](../handoff/audit/WIP_20260923_CONTINUATION_FRONTIER_R1.md)은 115/115/115·다른 SHA; [2026-09-21 72/72 disposition](../handoff/audit/20260921b_FRONTIER_DISPOSITION.md)은 과거 114계획 편성 | 현재 123계획·81 non-DONE의 대체 증거가 아니다. |

**왜 재발했나.** §6.2의 약속은 “새 큐마다 현재 frontier artifact/SHA를 인계에 묶고 모든 disposition_required 행을 checker가 대조한다”였다. 실제 [frontier_audit.py](../scripts/frontier_audit.py) --check의 종료코드는 물리 계획 ID와 색인 ID의 집합 차이만 반영한다. 출력의 conflicts가 양수여도 그 자체로 실패하지 않고, preflight_count는 설계 preflight 통과 수가 아니라 live launcher 수다. [test_frontier_audit.py](../scripts/test_frontier_audit.py)는 오래된 P014·새 P097의 집합 보존만 시험한다. [handoff_queue.py](../scripts/handoff_queue.py)와 [Codex 핸드오프 검사기](../.agents/skills/session-handoff/scripts/check_handoff_codex.py)는 **직전 미완료 배치의 계승**·섹션 구조·시간 미달 문구는 보지만, 현재 frontier SHA나 81개 ID의 판단표를 요구하지 않는다. 따라서 GPT가 현재 frontier를 새 큐의 실제 입력으로 읽지 않아도 정적 61종과 handoff 린터가 녹색이었다.

이는 정적 검사기가 자기 계약인 P=F를 어긴 것이 아니라 **계약이 큐 소비까지 닿지 않았고 GPT도 절차를 빠뜨린** 사례다. 2026-09-21 M3/M4의 일회성 성공을 지속 강제로 읽은 상태 표현 역시 오해를 키웠다. M5 사용자 큐 3회 운영 증거가 없는 점은 별도 미완료이지 이번 GPT 측 감사 누락의 핑계가 아니다. 현재 79개 HOLD의 개별 우선순위 판단은 미확인이나, 빠진 READY 팔이 있었다고 단정하지 않는다.

### 6.6 보완 계약 — 큐가 바뀔 때만 현재 frontier를 강제한다

새 audit 문서를 매 세션 무조건 늘리지 않는다. 권장 실험 §7의 **집합·순서·시간·실행상태가 바뀌는 경우**에만 입력 문서 해시로 frontier JSON 한 건과, 필요할 때 동일 stem의 Markdown 한 건을 만든다. source manifest가 같으면 기존 산출물을 재사용한다. 현재 handoff는 그 정확한 경로·frontier SHA와 non-DONE 각 ID의 INCLUDE/EXCLUDE/HOLD 판단을 한 번씩 연결한다.

별도 checker는 (1) 현재 source manifest와 artifact가 동일한가, (2) disposition_required 집합과 판단표 집합이 정확히 같은가·중복 0인가, (3) INCLUDE 실물·id·시간이 §7 및 TSV/디스크와 일치하는가, (4) 충돌 행을 종료코드 0으로 숨기지 않는가, (5) 48h 미달 시 미포함 READY가 0인가 또는 가치/권한 때문에 보류한 이유를 사용자에게 명시했는가를 검증한다. 마지막 항목은 저가치 런으로 48h를 강제하지 않으면서 누락과 의도적 제외를 구별한다. 이 checker는 기존 handoff_queue의 **직전 큐 무손실 계승**을 대체하지 않고 보완한다.

회귀 fixture에는 계획 ID 집합은 그대로지만 launcher·결과만 바뀐 stale artifact, 한 ID disposition 누락, conflicts>0인데 기존 --check가 0을 반환하는 경우, 일반 문구만 있는 48h 미달, 오래된 P014D와 최신 P105의 동시 존재를 넣는다. 구현 전에는 큐 변경 문서에 FRONTIER_COVERAGE_NOT_VERIFIED를 명시하고, 구조 검사 PASS를 FRONTIER_CONSUMED나 과학적 우선순위 PASS로 승격하지 않는다. 이번 요청은 **제안서 보완**이므로 검사기·훅·핸드오프 양식 코드는 수정하지 않았다; 기계 강제 구현은 별도 명시 지시와 검증 뒤 착수한다.

## 7. 거절하면 못 하는 것

실험 자체는 계속할 수 있다. 다만 최신 세션에서 만든 계획이 오래된 승인·진행 계획을 계속
밀어내고, 사용자가 누락을 발견할 때마다 큐를 다시 작성하는 비용이 반복된다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 자동 상태 오분류 | 일부 단계 완료를 계획 전체 종결로 승격 | 종결은 `-done` 또는 계획 상단의 명시적 전체 종결 근거만 허용; 애매하면 진행 중 |
| 저가치 실험으로 48h 채움 | READY는 많지만 질문 가치가 낮음 | 48h는 할당량이 아니라 감사 기준으로 유지; 가치·선결을 함께 기록 |
| 계획 문서가 낡음 | frontier가 낡은 상단 문구를 읽음 | 결과문서 최신 번호와 계획 §이력을 교차 확인하고 충돌을 오류로 출력 |
| 새 검사도 안 읽힘 | checker가 종합검사 밖에 존재 | `check_static_all.py`에 연결하고 회귀 fixture 추가 |
| Windows 검사만 통과하고 WSL SH는 미검사 | live 큐가 있는데 preflight 학습 호출 0건 | BAT·SH 공통 호출 추출과 WSL fixture를 종합검사에 연결; 0건 성공을 금지 |
| 표가 다시 날짜별 append로 증식 | 동일 P번호가 여러 행에 등장 | one-plan-one-row checker가 즉시 실패 |
| 구조 검사 PASS를 현재 큐 전수감사로 오인 | --check는 P=F만 확인하고 handoff는 frontier SHA 없이도 통과 | §6.6의 현재 artifact·전수 disposition checker를 큐 변경 시 강제; 미구현 동안 FRONTIER_COVERAGE_NOT_VERIFIED |

계측 위험을 반드시 하나 이상 적는다. 이 저장소 사고의 대다수가 계측이었다.

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| A | 최신 handoff·리뷰만 보고 큐 편성 | 빠름 | 이번 13.3h 누락을 반복하고 오래된 계획을 구조적으로 잊음 |
| B | 매 세션 사람이 113개 계획서를 전부 수동 판독 | 새 도구 없음 | 2~4h 반복비용, 일관성·재현성 없음 |
| C | 단일 상태 색인 + frontier 감사기 + 48h 포함/제외 근거 | 누락을 기계로 드러내고 과거·신규를 같은 기준으로 비교 | 초기 구현 2~4h, plan 상단 상태 유지 필요 |
| D | 아무것도 안 한다 | 비용 0 | 사용자 지적이 있어야 누락을 발견 |

### ★권장안과 근거

**C안을 승인·착수했다.** M0·M1과 M2의 수동 기준선(9건 false ongoing 교정·P087 복구)은 앞선
사용자 지시로 수행했고, 2026-09-21 M2 자동 inventory compiler와 old/new plan fixture를 구현했다.
M3의 2026-09-21 artifact·72/72 coverage와 M4의 51.1h 편성은 그때의 한 차례 증거다. 2026-09-25 새 큐의 현행 artifact·81/81 coverage 및 M5의 3회 운영 증거는 아직 없다. 계획 상태를 자동으로
“종결”시키지 않고 결과·registry 충돌을 보고하는 보수적 감사기로 만든다. 이번 재감사에서 발견한
BAT 전용 `dryrun_batch`는 WSL SH까지 읽도록 수정하고 회귀를 정적 묶음에 연결했다.

### 2026-09-25 재발에 대한 보완안 비교

| 보완안 | 내용 | 장점 | 단점·영향도·수행비용 |
|---|---|---|---|
| A — 사람 체크 | 작성자가 현재 frontier hash와 모든 non-DONE 판단을 수동 대조 | 코드 변경 없음 | GPT가 또 생략해도 통과; 문서 영향 낮음, 반복 검토비 높음 |
| **B — 현재 SHA·전수 coverage 게이트** | §7 변경 때만 산출물/판단표를 만들고 checker가 현재 입력·전체 ID·큐 행을 대조 | 이번 누락을 종료 전 실패로 만들며 audit 문서 증식을 제한 | checker/fixture·handoff 계약 변경 필요; 영향 중간·구현/검증 ⚙1~2h |
| C — 감사기의 우선순위·큐 자동 생성 | READY 팔을 자동 편성 | 누락 위험은 낮으나 과학적 가치·권리·시간 trade-off를 코드가 대신 결정; 영향 높음·유지비 높음 |

**보완 권장 B.** 원 승인 C안의 미구현 “현재 큐가 frontier를 소비했는가” 부분을 기계적으로 닫는다. 현 컴파일러상 READY0·GATED2·HOLD79이므로 0.2h 자체를 오류로 규정하지 않고, 모든 HOLD의 최신 선결과 제외 근거가 실제로 검토됐는지를 검증 가능하게 한다. 이 턴은 분석·문서 보완만 수행하며 코드 강제나 M5 완료를 선언하지 않는다.

### 2026-09-25 후속 C2 — 프론티어 감사의 자동 발동 지점

원 승인 C안의 자동 inventory 컴파일과 앞 절 보완 B안의 coverage 검사를 결합한다. C1(우선순위까지 자동 생성)은 채택하지 않는다. **C2는 감사 발동·누락 차단만 자동화하고 과학적 우선순위는 Codex·사용자가 정한다.** 앞 절의 “코드 미변경”은 1차 보완 당시 기록이며, 아래는 이번 사용자 구현 지시의 별도 후속이다.

| 발동안 | 작동 시점 | 반복 누락 방지력 | 대가·판정 |
|---|---|---|---|
| 스킬 문구만 추가 | AI가 핸드오프를 쓸 때 | 낮음 — 과거에도 문구는 있었으나 빠뜨림 | 코드0, **단독 강제안 아님** |
| PreToolUse 훅 | 셸·패치 호출 전 | 낮음 — 최종 §7과 source manifest가 확정되기 전 발화; hash 재신뢰·fail-open/E2E 부담 | 지금 도입 안 함 |
| handoff 생성기만 | 템플릿 생성 시 | 중간 — 이후 AI가 큐를 교체하면 초기 감사가 낡음 | 경고 placeholder로만 사용 |
| **WIP close + 현재 handoff 검사** | §7 편성·원장 완료 뒤 | 높음 — 현 frontier/큐 SHA·전수 ID·실물/시간을 검사하고 미충족 시 close 거부 | **C2 채택**. 큐/핸드오프 지시 없는 WIP에는 적용하지 않음 |

**구현 계약.** [frontier_queue_gate.py](../scripts/frontier_queue_gate.py)는 현재 계획·색인·TSV·COMPASS·기준표·결과·활성 리뷰에서 frontier를 다시 컴파일한다. source SHA와 §7의 배치/id/시간/실행상태 SHA로 이름을 정한 **한 JSON**을 handoff/audit에 만들며, 입력이 같으면 재사용·덮어쓰기 금지다. 물리/색인 차이 또는 충돌행은 생성부터 거부한다. non-DONE 각 ID를 정확히 한 번 싣고 실물 런처가 있는 계획은 REVIEW_REQUIRED로 시작한다. 실물 0건인 계획의 AUTO_NO_LAUNCHER/HOLD는 **지금 실행 가능한 런처가 없다는 재고 사실**이지, 그 계획의 과학적 가치 평가를 완료했다는 뜻이 아니다.

AI는 현재 §7에 올린 live-plan의 INCLUDE 이유를 수동으로 적고, 올리지 않은 live-plan은 EXCLUDE/HOLD의 구체 사유를 적는다. READY를 빼려면 사용자 승인 참조가 필요하다. 검사기는 artifact source manifest·queue SHA 최신성, 모든 non-DONE ID coverage·중복0, §7 실물/TSV 시간/WSL 메뉴 id, INCLUDE↔§7 일치, 미검토 live-plan, 충돌행을 실패로 처리한다. [new_handoff.py](../scripts/new_handoff.py)의 §7 골격은 FRONTIER_COVERAGE_NOT_VERIFIED를 명시하고, [wip.py](../scripts/wip.py)의 queue/핸드오프 지시 원장은 --close 때 정확한 --handoff를 요구해 [현재 frontier marker](../scripts/frontier_queue_gate.py)를 검사한 뒤에만 -done으로 옮긴다. 기존 static-audit hash gate는 그대로 선행한다.

**실행 순서:** 현재 핸드오프의 §7을 확정 → frontier_queue_gate.py --prepare --handoff로 재사용 가능한 JSON 생성 → live-plan REVIEW_REQUIRED를 수동 disposition으로 채움 → §7에 출력 marker 한 개를 넣음 → 같은 도구 --check → codex-safe 정적 감사 → wip.py --close --static-audit ... --handoff ... . `--prepare`는 실험·GPU·모델을 실행하지 않고, `--check`는 읽기 전용이다. 진행 중 큐 잠금의 UNVERIFIED 행은 frontier/런처 접근을 피하고 종료를 거부해 기존 WIP를 열어 둔다.

**검증 수준·잔여:** [격리 회귀](../scripts/test_frontier_queue_gate.py)는 누락 marker, stale source/queue, 빠진 ID, conflict, BAT→WSL SH 대응과 역사 MISSING/HOLD 보존을 확인한다. [WIP 회귀](../scripts/test_wip.py)는 queue 원장이 --handoff나 유효 marker 없이 닫히지 않음을 확인한다. 두 회귀는 [정적 묶음](../scripts/check_static_all.py)에 연결한다. 이는 C2의 코드/합성 정적 증거일 뿐 새 Codex 세션·사용자 smoke E2E나 M5 3회 운영 증거가 아니다. AUTO_NO_LAUNCHER 계획의 구현 가치·선결 우선순위는 별도 사람 감사로 남으며, C2가 모든 연구계획의 가치 평가를 자동 완료했다고 주장하지 않는다.

**상태:** C2 코드·격리 회귀 PASS. 현재 handoff의 artifact는 non-DONE81/81·live 수동 INCLUDE2로 --check 오류0, 이번 실제 WIP close는 --handoff 누락 exit2로 거부하고 정확 handoff+static audit에서는 -done으로 닫혔다. 이는 **현재 로컬 종료 경로의 관찰**이지 신규 사용자 smoke·다른 세션 3회 운영 증거가 아니다. AUTO_NO_LAUNCHER79의 과학적 가치 심사와 M5는 미완료이므로 제안서 done 이관·전체 ACTIVE_VERIFIED는 선언하지 않는다.

### 2026-09-25 후속 C2b — 결과문서 본문 변경의 artifact 충돌 교정

이번 P105 결과097에 원답안 정성 절을 추가했을 때 결과문서 SHA는 바뀌었으나 frontier 행의 latest_result=097과 빈 큐는 같아 종전 파일명 FRONTIER_QUEUE_B7A0440D34FF_4F53CDA18C2B.json이 재사용됐다. 종전 prepare는 파일이 존재하면 원천 manifest를 대조하지 않고 반환하고 check는 stale manifest를 거부한다. 검출은 정상이나 새 핸드오프를 닫을 새 artifact를 만들 경로가 없던 결함이다. 과거 JSON을 덮어써 역사 증거를 바꾸지 않는다.

사용자 승인에 따라 두 번째 파일명 해시를 큐만이 아니라 현재 source_manifest와 queue_rows의 결합 SHA-256으로 바꿨다. 같은 frontier 행 SHA·빈 큐에서도 새 이름 FRONTIER_QUEUE_B7A0440D34FF_F6990B83D1BD.json이 생기며, JSON의 순수 queue_sha256 필드는 그대로다. 격리 회귀는 결과 본문만 수정→frontier 행 SHA 동일→새 artifact 생성→구 artifact byte 불변→옛 marker stale 거부→새 marker 수동 live 판정 후 PASS를 검증한다. C2 회귀 7/7은 CPU 임시트리 증거이며 사용자 새 smoke는 E2E_NOT_RUN이다.

**남은 별도 문제 — 과학적 우선순위:** 물리/색인123/123 중 미종결81(계획25·진행56)은 현재 연구 런처0이라 모두 AUTO_NO_LAUNCHER/HOLD로 자동 등록된다. 이 표지는 가치·구현가능성 심사가 아니다. first_unfinished_stage 38/81이 미식별이고, first_prerequisite는 현재 단계가 아니라 본문에서 처음 보인 “선결” 문장을 택해 P014E G0 완료 문구나 P029 옛 미판독 문구를 가리킬 수 있다. preflight_count도 실제 preflight PASS 수가 아니라 live launcher 수다. COMPASS 검사기는 결과문서 번호만 대조하므로 결과097의 새 §7이나 review_request의 1차 SFT 검수를 자동 감지하지 못한다. C2b가 동작해도 0런처를 “목표 달성” 또는 전수 과학 심사 완료로 해석하면 안 된다.

| 향후 보완안(미승인) | 장점 | 대가·제약 |
|---|---|---|
| A. 현재 C2와 작성자 수동 기억 유지 | 코드0 | 자동 HOLD 뒤 구현 우선순위를 또 놓칠 수 있음 |
| **B. C3 수동 의미 triage 종료 게이트** | 런처0·미종결 계획이 있으면 오래된/새 계획의 BUILD_NEXT·USER_DECISION·FAILED_GATE·LOW_PRIORITY 근거와 다음 구현 한 건 이상을 인계에 요구; 과학적 선택은 사람 담당 | 현재 단계 필드 정규화·checker/fixture 필요 |
| C. 81개 전부의 구조화 단계 manifest와 매 큐 수동 재승인 | 누락 탐지 가장 강함 | 문서·유지비와 재검토 부담 큼 |

**권장 제안은 B지만 구현 승인은 아직 없다.** 이번 승인 범위는 C2 artifact 충돌 수정·회귀뿐이다. 기존 M5 3회 사용자 큐 운영과 C3 의미 심사는 계속 미완료다.

### 2026-09-25 후속 C3 — 수동 의미 triage 종료 게이트 승인

사용자가 앞 절의 B안을 승인했다. 이전 문단의 미승인 표기는 당시 기록이고, 이 절 이후에는 C3 승인 범위가 우선한다. C2는 물리계획 123/123 및 미종결 81/81의 집합만 확인했으며 연구 런처 0건 때문에 81건 전부 AUTO_NO_LAUNCHER/HOLD였다. 이는 과학적 가치판정이 아니다. 별도로 루트의 approved-on-going 제안서 20건도 기존 frontier 집합에 포함되지 않아 연구·작업방식 진행항목을 누락할 수 있었다.

권장 C3 구현은 계획마다 가치 등급과 BUILD_NEXT / USER_DECISION / FAILED_GATE / LOW_PRIORITY / EVIDENCE_NEEDED / DOC_CORRECTION 중 하나, 근거·증거·다음 행동을 수동 기입한다. BUILD_NEXT는 중복 없는 순위를 매긴다. 승인 진행 제안서 20건도 IMPLEMENT_NEXT / USER_DECISION / FAILED_GATE / E2E_PENDING / LOW_PRIORITY / DOC_REFRESH로 각각 분류한다. 템플릿은 모두 REVIEW_REQUIRED에서 시작하므로 런처 부재만 이유로 자동 종료하지 못한다. 적어도 한 다음 구현이 없으면 사용자의 명시적 no-build 승인 참조가 필요하다.

현재 source manifest와 제안서 SHA에 결합된 별도 C3 artifact를 handoff/audit에 두고, 새 핸드오프 §7의 독립 marker와 scripts/wip.py --close의 fail-closed 검사를 연결한다. C2의 큐 인벤토리 marker는 유지하며 C3가 이를 대체하지 않는다. 사용자 모델·GPU·스모크는 실행하지 않고, C3 정적 회귀와 실제 새 세션 E2E를 분리한다. 81+20 수동 검수의 반복 비용과 형식적 복제 위험이 남으므로 근거의 과학적 타당성은 여전히 사용자·Codex의 검토 대상이다. M5 3회 운영이 끝나기 전 done 이관하지 않는다.
