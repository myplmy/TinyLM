# Codex compact hook 효율성 감사 — 2026-09-19

## 1. 범위와 결론

사용자 지시에 따라 guard `PreToolUse`는 제외했다. 현재 프로젝트의 나머지 hook은
`PreCompact(manual|auto)`와 `SessionStart(source=compact)` 한 쌍뿐이다.

결론은 **제거하지 않고 좁게 개선**이다. 플랫폼 자동 압축은 일반 대화 요약을 만들고, 프로젝트
hook은 session ID에 정확히 결합된 WIP의 승인·NOT_RUN·보호경계를 추가한다. 둘은 대체 관계가
아니다. hook은 auto compact 횟수를 결정하지 못하며, Codex가 해당 lifecycle event를 보낼 때만
실행된다. 따라서 “한 지시에 압축이 여러 번 발생”한 원인을 이 command hook에서 찾을 근거는 없다.

## 2. 공식 계약 대조

[OpenAI Hooks 공식 문서](https://learn.chatgpt.com/docs/hooks)에 따르면 `PreCompact`는 수동·자동
압축 전에 호출되고 plain stdout은 model context가 아니다. 압축 직후
`SessionStart(source=compact)`가 `additionalContext`를 더해 다음 작업을 잇는다. context 추가는
누적되어 너무 크면 효율을 해칠 수 있고, transcript 형식은 안정 API가 아니다.

현재 구현은 이 계약에 맞게 다음처럼 역할을 분리한다.

| event | 역할 | 실패 정책 |
|---|---|---|
| `PreCompact` | 현재 session ID와 exact WIP·capsule hash를 사전 확인 | exact binding 중복·stale capsule만 fail-closed; foreign/unbound WIP는 선택하지 않고 경고 |
| `SessionStart(compact)` | 해시 검증된 8필드 capsule을 additive context로 주입 | 같은 routing 규칙; transcript를 읽지 않음 |

공식 문서에서 구현되지 않았다고 설명하는 `suppressOutput` 반환은 제거했다. `PreCompact`는
이제 성공 시 `{"continue": true}`만 반환한다.

## 3. “옛 핸드오프만 주입” 가설 검증

코드·회귀 fixture·현재 세션 process simulation은 이 가설과 일치하지 않는다.

- hook은 `handoff/*_HANDOFF.md`를 읽지 않고 root의 열린 `WIP_*_작업원장.md`만 열거한다.
- session ID가 정확히 일치하는 원장 하나만 고르며 다른 세션 원장을 빌리지 않는다.
- 회귀검사 `test_handoff_compact_text_is_not_read_or_replayed`를 포함한 14건이 통과했다.
- 현재 session `01a0b33b-d14e-7c40-ada8-229a1f97eabd` simulation은
  `WIP_20260919e_작업원장.md`, 완료 항목 1~4, 진행 항목 5를 포함했고
  `202609190446_HANDOFF` 문자열은 포함하지 않았다.

따라서 이전 compact에서 낡아 보인 핵심 원인은 WIP capsule의 “수행 변경·검증”이 **완료 항목만**
나열한 데 있다. 긴 항목이 진행 중인 동안 WIP가 바뀌어도 그 중간 작업은 capsule에 나타나지 않았다.

## 4. 이번 개선

- WIP capsule이 완료 산출물뿐 아니라 `🔄진행` 항목의 작업 내용과 중간 산출물도 담는다.
- 항목별 문자열과 전체 activity 문자열에 상한을 둬 context 폭증을 막는다.
- 현재 simulation의 전체 `additionalContext`는 2,093자다. 설정의
  `additionalContextLimit=1200`은 그대로 두며 token 수 PASS로 과장하지 않는다.
- material milestone마다 `scripts/wip.py`로 상태를 갱신해야 다음 compact가 새 내용을 받는다.
  WIP를 갱신하지 않은 채 반복되는 동일 주입은 hook이 transcript를 잘못 읽은 결과가 아니다.

## 5. 증거 수준과 사용자 조치

| 범위 | 판정 |
|---|---|
| Python syntax·WIP 12 tests·compact 14 tests | `STATIC_ONLY / PASS` |
| 현재 session ID direct process simulation | 정확한 WIP routing·2,093자 context `PASS`; Desktop lifecycle E2E를 대신하지 않음 |
| 과거 exact-WIP auto compact 사용자 관찰 | 과거 hash 범위 `ACTIVE_VERIFIED` |
| 이번 hook/WIP 변경 hash | `STATIC_ONLY`; `/hooks` 재검토·신뢰 후 새 auto compact 관찰 전 승격 금지 |
| manual compact | 사용자 검증 제외 결정 유지; `NOT_RUN` |

새 hash를 신뢰하기 전에는 hook 안전 기능에 의존하지 않는다. 신뢰 뒤에도 다음 실제 auto compact가
현재 진행 항목을 주입하는지 한 번 관찰해야 이번 변경 범위를 `ACTIVE_VERIFIED`로 올릴 수 있다.

## 6. 2차 이행 재감사 — 실제 hook command와 현재 WIP

`hooks.json`이 실제 호출하는 WSL 명령의 interpreter는 `/usr/bin/python3` 3.12.3이다. 이전
검증처럼 TLM conda Python을 대신 쓰지 않고 이 실제 명령으로 20회 process simulation했다.

| 항목 | 관측 |
|---|---:|
| `SessionStart(source=compact)` median | 34.18 ms |
| p95 | 43.49 ms |
| additional context | 1,742 chars |
| exact session WIP | `WIP_20260919f_작업원장.md` |
| 완료/진행 복구 | item3 완료·item5 진행 확인 |
| 옛 handoff 문자열 재생 | 0 |
| `PreCompact(auto)` | 정확히 `{"continue": true}`, warning/systemMessage 0 |

이는 command 자체가 짧고 정확한 현재 WIP를 선택한다는 process-level 증거다. Desktop이 한 지시에서
autocompact를 여러 번 일으키는 빈도는 이 hook이 결정하지 않는다. hook은 플랫폼 event를 받을
때만 실행되므로 제거해도 압축 횟수가 줄어든다는 근거가 없고, 제거하면 승인·NOT_RUN·보호경계의
exact-WIP 보강만 사라진다. 따라서 결론은 계속 **유지·개선**이다.

다만 이 simulation은 실제 Desktop lifecycle 호출이 아니며 현재 hash의 `ACTIVE_VERIFIED` 증거가
아니다. 새 hash trust 뒤 다음 실제 auto compact 관찰 전 상태는 `STATIC_ONLY / E2E_NOT_RUN`이다.

