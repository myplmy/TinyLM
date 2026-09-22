# 제안 — 실험결과 증거추적과 live-review 연쇄누락 재발 방지

> **작성** 2026-09-22 · **상태** ⏳판단 대기 · **분류** 작업방식
> 양식: [`proposal/README.md`](README.md) §3. 이 제안서는 구현 승인이 아니다.

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

로그 회수 작업마다 **명시적으로 주어진 증거 집합→결과문서→직접 소비 문서**를
한정 범위 closure로 기록하고, 정확한 backlink나 live-review disposition이 비면 세션 완료를
거부하는 계약을 만든다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| result-closure 감사 스키마 | `TINYLM_RESULT_CLOSURE_V1` JSON; 정확한 WIP/session·로그·JSON tag·결과문서·소비자·면제 사유 |
| 한정 검사기 | `scripts/check_result_closure.py --manifest <exact file>`; 자동 트리 발견 금지 |
| 회귀 fixture | raw-log 1건 누락, 축약 basename, live review 미처리, 정당한 `NOT_APPLICABLE`, 보호 경로 미접근 |
| 작업절차 갱신 | `log-to-result` 완료 절차와 Codex 01/02에 정확한 소유권·검증 순서 반영 |
| 세션 감사 증거 | `handoff/audit/<WIP>_RESULT_CLOSURE.json`; handoff에는 전문 복사 대신 링크·요약만 유지 |

이 성과물은 결과 수치를 중복 저장하지 않는다. 수치 정본은 계속 결과문서·JSON이고,
closure는 “어느 증거와 소비자를 검토했는가”만 소유한다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | **0 GPU-h** |
| AI 작업 | ⚙**4.5h**(스키마 0.5 + checker 1.5 + 통합 1.0 + fixture 1.0 + 문서 0.5) |
| ★**사용자가 직접 해야 하는 일** | ⚙**0.2h** 권장안·면제 정책 승인 검토 |
| 디스크 | 감사 JSON·fixture 합계 ⚙**1 MiB 미만** |
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

**외부 근거**: 없다. 이 제안은 외부 논문·상품이 아니라 저장소 내부 실사고의
완료 계약을 다룬다.

## 6. 방법

| 단계 | 무엇 | 비용 | ★**다음으로 가는 조건** |
|---|---|---:|---|
| M0 | 현 사고 fixture를 16-log/4-result/1-review 불변 케이스로 고정 | ⚙0.3h | 누락 12+1을 모두 재현 |
| M1 | `TINYLM_RESULT_CLOSURE_V1` 스키마: exact input paths·result mapping·active-review disposition·exemption reason | ⚙0.5h | 보호 경로와 수치 사본을 담지 않음 |
| M2 | 명시 manifest만 읽는 checker 구현 | ⚙1.5h | raw log basename 1건 삭제, review disposition 삭제 fixture를 각각 FAIL |
| M3 | `log-to-result`·WIP·codex-safe 감사에 closure 경로 결합 | ⚙1.0h | 같은 session/WIP/hash이 아니면 close 거부 |
| M4 | 5종 회귀·먱등성·UTF-8·상대링크 검증 | ⚙0.7h | valid fixture PASS, 모든 결함 fixture FAIL |
| M5 | Codex 01/02·skill·audit README에 소유권·한계 반영 | ⚙0.5h | 정적 PASS를 동적/과학 PASS로 승격하는 문구 0건 |

### active review 판독 규칙

checker가 의미를 추측하지 않도록 closure manifest에 review 행을 명시한다.

- 결과문서 링크 또는 계획번호를 직접 소비하고, 헤더가 검토 대기·진행 중인 리뷰만 후보다.
- `_absorbed`·`_superseded`·완료 snapshot은 자동 패치하지 않는다.
- 각 후보는 `UPDATED`, `NOT_APPLICABLE(reason)`, `USER_DECISION_PENDING(reason)` 중 하나를 가진다.
- 수치 변경이 없어도 상태·선결·`NOT_RUN`이 바뀌었으면 소비자 검토 대상이다.

## 7. 거절하면 못 하는 것

결과문서와 리뷰를 사람이 수동으로 계속 갱신할 수는 있다. 따라서 즉시 실험·학습이
막히지는 않는다. 다만 중단·compact 후에도 입력 증거 전수와 live-review 처리를 기계적으로
증명할 수 없고, 같은 종류의 추적성 누락이 다시 나와도 기존 58종 정적 PASS가 막지 못한다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

**계측 위험**은 “문구가 있다”를 “증거 전수와 의미 연쇄가 완결됐다”로 오인하는 것이다.

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 포장만 늘어남 | 완료마다 WIP·handoff·static audit·closure에 같은 서술 복제 | closure에는 경로·hash·disposition만, 서술은 결과/handoff에만 둔다 |
| broad scan이 보호 경로를 접근 | 자동 발견이 `runs/`·보호 데이터를 열거 | manifest에 명시된 경로만 읽고 excludedPaths를 fail-closed |
| review 오탐 | 역사 snapshot을 매번 갱신하라고 FAIL | 파일 접미사·헤더 상태로 active 후보를 한정하고 면제 사유 허용 |
| 자기 사본과 대조 | manifest를 결과문서에서 자동 추론해 항상 PASS | 입력 로그 목록은 사용자 지시/WIP에서 독립적으로 고정 |
| 문구 존재만 통과 | 로그명이 있지만 판정과 연결되지 않음 | section-level mapping·result document mapping을 manifest에 기록 |
| 완료 차단의 경직성 | 무관한 review 후보 하나로 WIP close 불가 | `NOT_APPLICABLE(reason)`를 허용하되 빈 사유는 거부 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | 체크리스트만 강화: `log-to-result` 마지막에 raw-log·review 확인 문구 추가 | 구현 거의 0, 규칙 가벼움 | 이번에도 이미 문구는 있었으며 중단 후 다시 누락 가능 |
| **B** | 명시 closure manifest+한정 checker: 독립 입력 집합과 소비자 disposition을 JSON으로 고정 | 중단 복구, 재현 가능, 보호 범위 한정, 기존 정본 중복 최소 | 구현·fixture 비용 4.5h, 감사 파일 1개 추가 |
| **C** | 저장소 전체 의미 의존성 그래프: 모든 문서·수치·인용을 자동 추론 | 이론상 광범위 누락 감지 | 오탐·보호경로·역사 snapshot 소급·유지보수 비용이 크고 함정 43 재발 가능 |

### ★권장안과 근거

**B. 명시 closure manifest+한정 checker**를 권장한다. A는 이미 있던 서술 규칙을 반복하므로
재발 방지력이 낮다. C는 자동화 범위가 필요 증거보다 넓고 오탐·보호 경계 비용이 크다.
B는 사용자가 주어진 exact 로그 목록을 바깥 증거로 보존하면서, 상위 review의 의미 판단은
자동 추측 대신 명시 disposition으로 남겨 현 정본 구조와 안전 경계를 가장 잘 유지한다.
