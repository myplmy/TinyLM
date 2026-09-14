# A06 v03 의미 재서술 사전 변경 계획 — locator 80 r2 (2026-09-14)

- precondition: source v03 `6D178EC8E0B228D18734AF86380CD1F1E62C33D0126AEF58714BD2F5027CBB7D`, registry `0AE5A66695BE822F322553E65BD9E5A4C178DD130C2E5811269E50D3C9D55D4C`.
- source locator 80의 `concept`·`text`와 같은 registry locator의 `primary`만 바꾼다. relations `state, comparison, other`, `other_type` `센서 채널 불일치`, 모든 비-primary registry field, 행 순서와 비대상 바이트는 보존한다.

| locator | 기존 concept | 새 concept | 직접 판단 |
|---|---|---|---|
| 80 | 작업 기록이 없을 때 압력 조절기 경보를 단독으로 판단하지 않는 기준 | 압력 조절기 경보의 보류 기준 | 작업 기록과 채널별 압력값이 맞지 않을 때 경보 해제를 보류한다는 뜻을 짧고 독립적인 명사구로 쓴다. |

새 text에는 압력 센서·작업자 기록·채널 불일치, 담당자의 비교·보류 판단, 실제 이상 누락과 불필요한 설비 정지를 막는 결과를 명시한다. updater의 원복 backup은 `A06_registry_before_v03_semantic_rewrite_80_r2_2026-09-14.jsonl`이다.
