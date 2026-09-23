# 제안 — 실험결과 증거추적과 live-review 연쇄누락 재발 방지

> **작성** 2026-09-22 · **상태** ✅결과문서 한정 B안 승인·진행 중 · **분류** 작업방식
> 양식: [`proposal/README.md`](README.md) §3. 2026-09-23 조건부 승인이다. 아래 원안의 review 관련 구현 조항은 §9.1로 대체한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

2026-09-22 실험 회수에서 16개 원본 로그와 4개 결과문서(069/078/082/088)를
판독했다. 결과 수치·판정·조건서명·재현명령·계획·목록·기준표·methods·COMPASS는
반영했고 codex-safe 정적 검사 58종도 오류 0이었다. 그러나 후속 감사에서 두 가지가
누락된 것을 확인했다.

| 누락 | 실측 | 왜 중요한가 |
|---|---:|---|
| 결과문서의 정확한 raw-log backlink | 16건 중 **12건**의 basename이 축약·미기재 | 결과문서만으로 원본 증거를 전수 역추적하기 어려움 |
| 살아 있는 상위 리뷰 갱신 | **1건**, `6차리뷰` | A 후보의 LR1.5 증거와 P014D/P025B/P060B 현재 판정이 없 상태로 사용자 검토를 기다림 |

이는 실험 수치 오판이 아니라 **완료 계약의 빈 경계**다. 중간 중단·compact는
누락을 드러내는 계기였지만, 작업이 끝까지 이어졌어도 현 검사만으로는 두 누락을
기계적으로 거부하지 못했다.

### 기존 검사기가 이 역할을 하지 못한 이유

| 기존 검사 | 실제 소유 질문 | 이번 누락을 못 잡는 이유 |
|---|---|---|
| `append_repro.py` | launcher 명령이 결과문서에 보존됐나 | 입력 raw log 목록을 모름 |
| `check_result_conditions.py` | 비교조건·허용 주장이 완결됐나 | provenance 파일·상위 소비자를 검사하지 않음 |
| `check_links.py` | Markdown 상대링크 대상이 존재하나 | backtick basename·축약표기는 링크가 아님 |
| `check_index_sync.py` | 알려진 색인이 산출물을 담았나 | review의 의미·숫자 최신성을 모름 |
| `check_compass.py` | 12개 축의 인용 번호가 낡았나 | COMPASS만 소유하며 `docs/review/` 초안은 대상 아님 |
| WIP/handoff 검사 | 지시·상태·인계 형식이 완결됐나 | “바뀐 결과의 모든 직접 소비자” 집합을 소유하지 않음 |

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

로그 회수 작업마다 사용자가 지정한 **독립 raw-log 목록→정확한 결과문서 절**
대응을 검증하여, 누락·축약된 증거 파일명으로 결과 회수를 완료 처리하지
않는 계약을 만든다. review 문서의 탐색·갱신·완료 차단은 승인 범위가 아니다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태·현재 상태 |
|---|---|
| 결과 closure manifest | `TINYLM_RESULT_CLOSURE_V1`; WIP/session, 독립 입력 raw-log 경로, 정확한 결과문서·절 매핑, 면제 사유만 소유. review/consumer 필드는 금지. 스키마 설계됨 |
| 한정 검사기 | `scripts/check_result_closure.py --manifest <exact file>`; 명시 경로만 확인, raw log **내용은 읽지 않음**. 합성 fixture PASS |
| 회귀 fixture | 정상·입력 누락·절 내 basename 누락·review 필드 거부. 실제 2026-09-22 사고 전수 재현은 큐 잠금으로 `NOT_RUN` |
| 작업절차 | `log-to-result`에 result-only 적용·큐 잠금 우선 규칙 추가. Codex 01/02와 audit README 문서 규약은 반영, WIP/audit 자동 연동은 미완 |
| 세션 감사 증거 | 결과 회수별 독립 manifest와 checker 출력. 결과 수치·review 상태를 복제하지 않음; 실물 작성 `NOT_RUN` |

closure의 PASS는 지정한 증거 이름과 결과 절의 추적성만 뜻하며, 결과의
수치 정확성·과학적 타당성·review 최신성을 증명하지 않는다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | **0 GPU-h** |
| AI 작업 | ⚙**3.8h**(결과 한정 스키마·checker·연동·fixture·문서 추정; 실제 투입시간 아님) |
| ★**사용자가 직접 해야 하는 일** | 조건부 승인 완료. 실물 적용 때 입력 로그 집합·면제 사유 확인 ⚙0.2h 추정 |
| 디스크 | manifest·fixture 합계 ⚙**1 MiB 미만** |
| 외부 서비스·네트워크 | **0회** |

## 5. 원리·근거

**우리 실측**

| 근거 | 값 | 출처 |
|---|---:|---|
| 입력 raw log | 16건 | 2026-09-22 사용자 지정 목록 |
| 정확한 basename 누락 | 12건 | 결과 078/088 후속 감사 |
| 낡은 live review | 1건 | `docs/review/202609181843_6차리뷰_...md` |
| 종전 codex-safe 검사 | 58종 오류 0 | `handoff/audit/WIP_20260922_STATIC_AUDIT.json` |
| 재현 명령 보존 | 16 launcher, 추가 명령 0건 | `append_repro.py` 재감사 |

이 조합은 “현 검사가 나쁜 검사”라는 뜻이 아니다. 각 검사기는 자신의 소유 질문을
제대로 검사했지만, **input evidence coverage**와 **downstream consumer disposition**이 아무 도구의
입력이 아니었다. 재발 방지는 기존 검사기를 포장하는 것이 아니라 이 두 집합의
소유자를 추가하는 것이어야 한다.
현재 승인에서는 두 누락 중 **input evidence coverage만 구현**한다.
review 누락은 역사적 사고 사실로 남지만 새 checker의 실패 조건이 아니다.

**외부 근거**: 없다. 이 제안은 외부 논문·상품이 아니라 저장소 내부 실사고의
완료 계약을 다룬다.

## 6. 방법

| 단계 | 결과문서 한정 작업 | 비용 | 다음으로 가는 조건·현재 |
|---|---|---:|---|
| M0 | 사용자 지정 16-log/4-result 역사 입력을 독립 manifest fixture로 고정 | ⚙0.3h | 실제 로그 접근 잠금으로 `NOT_RUN`; 합성 축소 fixture만 PASS |
| M1 | exact raw-log·result path·section·status·reason 스키마. review/consumer 필드 금지 | ⚙0.5h | 코드에 일부 구현, 문서 스키마·session/WIP hash 결합 미완 |
| M2 | 명시 manifest만 읽는 checker | ⚙1.3h | 정상/입력 누락/절 basename 누락/review 필드 거부 합성 fixture PASS; 실물 `NOT_RUN` |
| M3 | `log-to-result`·세션 감사·WIP 종료 전 결과 closure 증거 결합 | ⚙0.8h | skill만 갱신, 세션 도구 자동 연동 미구현; 현재 큐 종료 전에는 실물 대상 금지 |
| M4 | 중복·축약·경로 traversal/symlink·UTF-8·면제 사유·session 불일치 회귀 | ⚙0.5h | 일부 합성 검사 PASS, 전수 회귀 미완 |
| M5 | Codex 01/02와 감사 README에 결과 전용 소유권·한계 반영 | ⚙0.4h | 문서 규약 정적 반영 완료, 실제 세션 자동 연동은 M3 잔여 |

검사기는 `test_result/`의 정확한 1단계 파일 경로만 받는다.
로그 존재와 basename을 확인하되 **원본 로그 내용은 열지 않는다**.
현재 사용자의 진행 중 큐 잠금은 이 검사기보다 우선하므로 해당
실물 manifest를 만들거나 검사기를 실행하지 않는다.

### 명시적 비목표

`docs/review/**` 후보 탐색, review 의미 판독·갱신·disposition,
review 미갱신을 이유로 한 WIP 종료 거부는 **구현하지 않는다**.

## 7. 거절하면 못 하는 것

결과문서의 raw-log basename을 사람이 수동으로 전수 대조할 수는 있다.
그러나 중단·compact 뒤에는 **사용자 입력 로그 집합 중 한 건이
결과문서에서 빠졌는지**를 독립적으로 재검증하기 어렵다.
review 최신성은 이 승인과 무관하며 본안을 거절하거나 채택해도
별도의 수동 문서 관리 질문으로 남는다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

**계측 위험**은 basename이 존재한다는 사실을 수치·판정의 유효성으로
확대하는 것이다.

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 포장만 증가 | WIP·handoff·audit·closure에 같은 설명 복제 | closure는 경로·절·hash·status만, 해석은 결과문서에 둠 |
| 보호 경로 탐색 | 자동 발견이 원본 cache·보호 데이터를 열거 | exact manifest 외의 경로를 금지하고 symlink·traversal 차단 |
| 자기 사본과 대조 | 결과문서에서 입력 로그 목록을 역추론해 항상 PASS | 입력 집합은 사용자 지시/WIP에서 독립 고정 |
| 문자열만 통과 | 정확 basename이 다른 결과 절에 존재 | exact Markdown heading의 해당 절에서만 찾음 |
| review 범위 침범 | checker가 review 경로나 disposition을 수용 | 스키마에서 review/consumer 필드 거부, review 파일 탐색 0 |
| 완료 차단 경직 | 결과 회수와 무관한 사유로 전체 WIP를 차단 | 결과 회수 입력 집합에만 적용, 면제는 비어 있지 않은 명시 사유 필요 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| A | result 문서의 raw-log 확인 체크리스트만 강화 | 구현 비용 작음 | 중단 후 전수성 재검증이 어려움 |
| **B** | 독립 입력 manifest와 한정 result-only checker | 누락·축약을 재현 가능하게 검출, 보호 범위 명확 | 감사 파일·fixture와 연동 비용 |
| C | 저장소 전체 의미 의존성 그래프 | 이론상 넓은 누락 탐지 | 오탐·보호 경로·유지보수 비용 큼 |

### 권장안과 근거

**B**를 권장한다. 사용자가 지정한 raw-log 목록을 결과문서와 독립적으로
고정하므로 사고의 12개 basename 누락을 직접 겨냥한다.
review는 검사 대상이 아니며 checker PASS를 review PASS로 쓰지 않는다.

### 9.1 2026-09-23 조건부 승인 및 진행 상태

사용자는 **결과문서 증거추적에만 B안을 승인**하고 review 적용을 명시적으로
제외했다. §1·§5의 review 누락은 역사적 사고 설명이지만 M0~M5의
집행 범위가 아니다. 파일명에 남은 live-review 표현도 역사적 제안 이름이다.

2026-09-23 현재 checker·합성 fixture·스킬 지침은 정적 구현됐지만
실물 회수 manifest, 세션 종료 자동 연동과 전체 회귀가 남아 `-approved-on-going`이다. 진행 중 큐의 로그와
런처 .sh는 승인으로 열리지 않는다.
