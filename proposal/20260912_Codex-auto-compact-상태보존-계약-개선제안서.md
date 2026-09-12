# 제안 — Codex auto compact 상태 보존 계약을 명시적으로 연결한다

> **작성** 2026-09-12 · **상태** ⏳판단 대기 · **분류** 작업방식
> 양식: [`proposal/README.md`](README.md) §3. 이 문서는 설계 제안이며, `.codex/**`,
> `.agents/skills/**`, `scripts/**`, Codex 02 및 핸드오프 양식의 실제 변경을 승인하지 않는다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

작업원장 12번은 “Codex의 자동 context compact가 핸드오프의 `compact 프롬프트` 절을
특별히 참고하는가”를 물었다. 기존 감사는 다음 두 사실을 구분했다.

1. 공식 Codex 설정에는 `compact_prompt`, `experimental_compact_prompt_file`,
   `model_auto_compact_token_limit`이 있다.
2. 저장소의 임의 Markdown 제목인 `## compact 프롬프트`를 Codex가 자동으로 찾아 읽는다는
   공식 계약이나 로컬 연결 설정은 없다.

두 번째 결론은 유지된다. 다만 후속 공식 문서 재감사에서 더 나은 제어점을 확인했다.
`SessionStart` 훅은 `source: "compact"`일 때 압축 직후, 다음 모델 요청 전에
`additionalContext`를 넣을 수 있고, 자동 압축이 한 턴 중간에 일어나도 즉시 이어지는 요청에
전달한다. 반면 `PreCompact`의 일반 stdout은 무시되며 이 훅은 압축을 중단할 수 있을 뿐,
그 자체가 동적 상태 주입 경로라는 보장은 없다.

쉽게 말해, 현재 핸드오프 코드블록은 이름만 “compact 프롬프트”일 뿐 자동 배선이 없다.
그러나 압축 뒤 WIP의 핵심 상태를 다시 넣어 주는 공식 훅 지점은 있으므로, 코드블록을 수동
복사하는 방식보다 검증 가능한 복구 경로를 설계할 수 있다.

로컬 범위 검사에서는 저장소 `.codex/config.toml`, 사용자 Codex 설정과 현재 훅에서
compact 관련 키·연결을 찾지 못했다. 따라서 현재 상태는 `DESIGNED`도 아닌 수동 문서 관례이며,
실제 보존 효과는 `E2E_NOT_RUN`이다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

압축기의 불투명한 내부 요약에 의존하지 않고도 현재 지시·권한·정확한 경로·완료 사실·미실행
사실·막힘·다음 행동이 압축 직후 모델 context에 다시 들어왔음을 E2E로 판정할 수 있는 단일
TinyLM compact 복구 계약을 만든다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| compact 보존 필드 계약 | 정확 보존 필드와 의미 보존 필드를 나눈 표준 명세 |
| 활성 작업 상태 캡슐 | 열린 WIP에만 두는 짧고 기계 판독 가능한 절 |
| 압축 전 게이트 | 열린 WIP 유일성·상태 캡슐 최신성을 검사하고 실패 시 압축을 중단하는 `PreCompact` 보조 훅 |
| 압축 후 재주입 | `SessionStart(source="compact")`가 검증된 WIP 상태 캡슐을 `additionalContext`로 전달하는 경로 |
| 회귀 fixture | 수동 compact와 자동 compact를 분리해 sentinel 8종 보존을 확인하는 검사 시나리오 |
| 핸드오프 양식 정리 | 자동 연결이 없는 `compact 프롬프트` 절을 제거하고 `정본 동기화·미갱신 사유`를 추가하는 동시 변경 |

이 산출물은 승인 뒤에만 구현한다. 이번 제안서 작성으로 생기는 것은 설계와 선택지뿐이다.

## 4. 비용

| 항목 | 양 |
|---|---:|
| GPU | 0 GPU-h |
| AI 작업 | ⚙ 4~7 engineer-h |
| ★**사용자가 직접 해야 하는 일** | ⚙ 20~40분: 신뢰된 새 세션에서 수동·자동 compact E2E 관찰 |
| 디스크 | ⚙ 1 MiB 미만(스크립트·fixture·짧은 로그) |
| 정상 턴 context | 상태 캡슐 길이만큼 압축 직후 1회 추가; 목표 ⚙ 300~700 tokens |

`compact_prompt`는 일반 매 턴용 개발자 지침이 아니라 압축 프롬프트 override다. 다만 실제
토큰 비용과 기본 프롬프트 대체 영향은 공식 문서가 수치로 보장하지 않으므로 E2E에서 측정한다.

## 5. 원리·근거

**우리 실측·저장소 사실**

| 근거 | 값 | 출처 |
|---|---|---|
| 핸드오프 compact 절 | 존재하지만 자동 소비 연결 0건 | `ai_dev_tool/Codex/02_핸드오프_규약.md`, 최신 핸드오프 |
| 저장소 compact 설정 | 관련 키 0건 | `.codex/config.toml` 범위 제한 검색, 2026-09-12 |
| 사용자 설정 compact 설정 | 관련 키 0건 | 사용자 Codex `config.toml` 범위 제한 검색, 2026-09-12 |
| 현재 상태 | `E2E_NOT_RUN` | 실제 수동·자동 압축 보존 fixture 미실행 |

**외부 근거 — 2026-09-12 실제 조회**

- OpenAI [Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)는
  `compact_prompt`를 history compaction prompt의 inline override로, 파일 방식은 experimental
  override로 정의한다. 자동 압축 임계치와 experimental context management도 별도 설정이다.
- OpenAI [Hooks](https://learn.chatgpt.com/docs/hooks)는 `PreCompact`가 manual/auto 압축 전에
  실행되고 `continue: false`로 중단할 수 있으나 일반 stdout은 무시된다고 명시한다. 같은 문서는
  압축 뒤 `SessionStart(source="compact")`의 `additionalContext`가 바로 다음 모델 요청에
  들어가며, 턴 중간 자동 압축에도 즉시 이어지는 요청으로 전달된다고 명시한다.
- OpenAI [Codex App Server](https://learn.chatgpt.com/docs/app-server)는
  `thread/compact/start`로 수동 압축을 일으키고 `contextCompaction` lifecycle을 관찰할 수 있게 한다.
- OpenAI [model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.2)는
  compact 결과를 불투명한 항목으로 취급하고 내부를 파싱하거나 그 구조에 의존하지 말 것을
  권한다. 따라서 “요약문 안에 문구가 남았는가”보다 “압축 직후 필요한 상태가 다시 모델에
  제공됐는가”를 검증하는 편이 안정적이다.

여기서 “임의 핸드오프 절은 자동 소비되지 않는다”는 결론은 문서에 그런 기능이 없고 로컬에도
배선이 없다는 사실에서 한 **추론**이다. 반대로 `SessionStart(source="compact")` 재주입은 공식
문서에 명시돼 있지만 TinyLM 환경에서 아직 실행하지 않았으므로 `ACTIVE_VERIFIED`가 아니다.

## 6. 방법

### 6.1 보존 계약 후보

압축 때 다음 여덟 필드를 상태 캡슐로 만든다. 경로·번호·상태 enum·명령·금지 대상은 문자열을
정확히 보존하고, 서술은 의미 동등성을 허용한다.

1. 현재 사용자 지시와 이번 턴의 변경 허용목록
2. 보호 경로·사용자 전용 실행·`NOT_RUN` 경계
3. 열린 WIP의 정확한 경로, 지시 총수, 각 미완료 번호와 상태
4. 이미 수행한 변경의 정확한 파일과 검증 결과
5. 막힘·승인 필요·미확인 사항
6. 사용자가 소유한 실행 중 프로세스·활성 파일
7. 폐기되거나 정정돼 다시 살아나면 안 되는 주장
8. 바로 다음 한 행동과 그 행동의 선결

상태 캡슐은 사실을 새로 판단하거나 완료 처리하지 않는다. 제안은 승인으로, `NOT_RUN`은 PASS로,
미확인은 실패로 바꾸지 않는다.

### 6.2 단계와 게이트

| 단계 | 무엇 | 비용 | ★**다음으로 가는 조건** |
|---|---|---:|---|
| M0 | sentinel 8종과 정확/의미 보존 판정표를 먼저 고정 | ⚙ 0.5h | 기대값·금지된 낡은 주장까지 fixture에 있음 |
| M1 | 열린 WIP에 300~700-token 상태 캡슐 계약과 생성·검증 함수를 설계 | ⚙ 1.0h | 한 개 열린 WIP만 선택하고 모호하면 무변경 실패 |
| M2 | `PreCompact`는 캡슐 누락·낡음만 검사하고 실패 시 중단하도록 설계 | ⚙ 0.5h | stdout 주입에 의존하지 않고 manual/auto 모두 fail-closed |
| M3 | `SessionStart(source="compact")`가 검증된 캡슐을 `additionalContext`로 재주입 | ⚙ 1.0h | 압축 직후 즉시 이어지는 요청에서 8필드가 보임 |
| M4 | 격리된 테스트 설정에서 `thread/compact/start` 수동 E2E | 사용자 ⚙ 10~20분 | 8/8 보존, 낡은 주장 0, 훅 오류 0 |
| M5 | 낮춘 임계치의 테스트 전용 프로필에서 자동 E2E | 사용자 ⚙ 10~20분 | 수동과 같은 8/8, 정상 세션 설정 오염 0 |
| M6 | 위 PASS 뒤 Codex 02·스킬·생성기·검증기를 한 커밋 단위로 정합 | ⚙ 1~3h | 핸드오프 compact 절 제거, 정본 동기화 절 추가, 관련 검사 PASS |

실패 시 M6로 가지 않는다. 특히 생산 `.codex/config.toml`의 `compact_prompt`를 먼저 바꾸지
않는다. 이 키는 “추가”가 아니라 “override”이므로 기본 압축 행동을 약화할 위험이 있다.

### 6.3 E2E 판정 예시

fixture에는 서로 헷갈리기 쉬운 값도 넣는다. 예를 들어 `WIP_...c.md`와 폐기된
`WIP_...b-done.md`, `NOT_RUN`과 `PASS`, 승인 대기와 완료를 함께 두고 압축 뒤 다음을 묻는다.

- 현재 열린 WIP 경로와 남은 번호는 무엇인가.
- AI가 절대 실행하지 않는 두 배치는 무엇인가.
- 사용자가 승인하지 않은 변경은 무엇인가.
- 폐기된 주장은 무엇이며 다시 사용하면 안 되는가.
- 다음 한 행동과 선결은 무엇인가.

모두 맞아야 PASS다. compact 산출물 내부 문자열을 파싱하는 검사는 만들지 않는다.

## 7. 거절하면 못 하는 것

현재 수동 핸드오프·WIP 절차는 계속 쓸 수 있다. 다만 `compact 프롬프트` 코드블록이 자동으로
사용된다는 보장은 계속 없고, 긴 작업 중 압축 뒤 권한 경계·정확한 경로·막힘이 유실돼도 이를
기계적으로 검출하거나 즉시 재주입할 수 없다. 따라서 핸드오프 절 제거도 승인 전에는 하지 않는다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| `compact_prompt`가 기본 프롬프트를 통째로 대체 | 요약 품질·도구 상태·완료 사실이 오히려 퇴행 | 권장안의 1차 경로에서는 쓰지 않고 격리 A/B 뒤 보조층으로만 검토 |
| 캡슐이 낡은 WIP를 재주입 | 이미 정정된 주장·완료 상태가 부활 | 생성 시 원장 상태·시각·열린 WIP 유일성 검증, 불일치 시 `PreCompact` 중단 |
| 훅이 보호 경로까지 검색 | 데이터 소유권 침범 | 루트 `handoff/WIP_*.md` 명시 경로만 열거하고 excluded path 접근 검사 |
| 압축 직후 context 중복·비대화 | 같은 상태가 반복되고 토큰 절감 감소 | 300~700-token 상한, exact field만 남기고 장문은 경로로 참조 |
| PostCompact 로그만 보고 보존 PASS 오판 | 훅 실행은 성공했지만 모델이 상태를 회수하지 못함 | 모델 질의 기반 8/8 E2E를 별도 PASS 조건으로 둠 |
| Desktop·CLI·App Server 경로 차이 | 한 경로에서만 동작 | 수동과 자동, 신뢰된 새 세션, 실제 사용 클라이언트를 분리 표기 |
| experimental 기능 의존 | 버전 갱신 뒤 동작 변화 | stable 문서화된 `SessionStart` 경로 우선, experimental 안은 별도 opt-in |

**프로젝트 영향 축**

| 영향 축 | 판정 |
|---|---|
| GPU·학습·모델 | 0; 학습과 모델 로딩 불필요 |
| 데이터·체크포인트·로그 소유권 | WIP만 읽게 제한하면 보호 데이터 영향 0; 재귀 검색은 금지 |
| 비교 유효성 | 실험 수치 변경 없음; 보존 fixture는 수동·자동 경로를 섞지 않음 |
| 증거 수준 | 문서 제안은 `DESIGNED`; 정적 PASS와 실제 compact E2E를 분리 |
| 문서 연쇄 | 승인 시 Codex 02·WIP·핸드오프 스킬·생성기·검증기를 동시에 바꿔야 함 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | 현행 핸드오프 `compact 프롬프트`를 사람이 필요할 때 복사 | 구현 0, 즉시 사용 가능 | 자동 연결·최신성·E2E 보장 없음; 제목이 실제 기능을 과장 |
| **B** | **권장:** compact 절은 핸드오프에서 제거하고, 열린 WIP 상태 캡슐 + `PreCompact` 최신성 게이트 + `SessionStart(source="compact")` 재주입 + 수동/자동 E2E를 결합 | 불투명한 요약 내부에 의존하지 않고 압축 직후 공식 경로로 상태를 복구; 동적 상태와 종료 스냅샷 역할 분리 | 훅·WIP·규약·검사기 동시 구현과 사용자 E2E 필요 |
| **C** | `.codex/config.toml`의 `compact_prompt`에 8필드 보존 규칙을 직접 넣음 | 압축 시점에 의도를 직접 전달, 구조 단순 | 기본 프롬프트 override 위험; 동적 WIP 내용 자체는 자동으로 가져오지 않음 |
| **D** | `experimental_compact_prompt_file`로 규칙을 별도 파일화 | 리뷰·버전 관리 용이 | experimental이며 C와 같은 override·동적 상태 문제 |
| **E** | `features.context_management.experimental_mode` 사용 | 단일 요약 반복 대신 notes·검색 이력을 사용하도록 설계됨 | experimental·계정 조건·기존 fixture 재설계 필요; TinyLM에서 미검증 |
| **F** | `AGENTS.md`나 `developer_instructions`에 보존 규칙 상시 삽입 | 매 턴 규칙 노출 | 매 요청 context 비용, 동적 상태 불포함, compactor 전용 계약이 아님 |
| **G** | `PreCompact`만으로 WIP 텍스트를 stdout 출력 | 구현이 쉬워 보임 | 공식 문서상 일반 stdout이 무시되므로 주입 수단으로 부적합; 중단 게이트로만 사용 가능 |
| **H** | 아무것도 바꾸지 않고 compact 절만 삭제 | 잘못된 자동성 암시 제거 | 실제 압축 유실 문제와 대체 상태 필드가 남음 |

### ★권장안과 근거

**B안을 권장한다.** 핵심은 “압축 요약에 문구가 반드시 들어갔는가”를 통제하려 하지 않고,
압축 직후 검증된 상태 캡슐을 다시 주입해 기능적으로 같은 정보를 보장하는 것이다. 공식 훅 계약과
가장 잘 맞고, `compact_prompt` override로 기본 동작을 깨뜨릴 위험도 피한다.

구현 순서는 B의 재주입·E2E를 먼저 검증하고, C는 보존율을 더 높여야 한다는 실제 실패가 있을
때만 격리 A/B한다. 현행 핸드오프 compact 절은 B가 `ACTIVE_VERIFIED`되기 전까지 바로 삭제하지
않고 “수동 보조·자동 계약 아님”으로 유지한다. B가 통과하면 핸드오프에서는 그 절을 제거하고,
대신 `정본 동기화·미갱신 사유`를 넣어 결과·계획·기준표·방법론·COMPASS의 반영 여부를 명시한다.

**승인 단위:** B안의 M0~M5 검증을 먼저 승인하고, PASS 뒤 M6 문서·스킬·도구 동시 정합을 별도
승인하는 2단계가 안전하다.
