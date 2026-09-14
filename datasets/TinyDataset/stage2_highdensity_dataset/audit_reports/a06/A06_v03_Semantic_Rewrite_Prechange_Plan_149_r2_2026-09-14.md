# A06 v03 의미 재서술 사전 변경 계획 — locator 149 r2 (2026-09-14)

- precondition: source v03 `AA828599509C0C4D5F802788EBA7D2EE6175B2CE50EC90383813815C96C79F57`, registry `1D99DB9B0EA83C5F8D99BEC4F6756E56B56D31DC02EC33F122605676919BA8FF`.
- source locator 149의 `concept`·`text`와 같은 registry locator의 `primary`만 바꾼다. relations `state, boundary, other`, `other_type` `후속 검증 누락`, 모든 비-primary registry field, 행 순서와 비대상 바이트는 보존한다.

| locator | 기존 concept | 새 concept | 직접 판단 |
|---|---|---|---|
| 149 | 제어기 신호가 부족할 때 환기창 위치를 정상 상태로 분류하지 않는 기준 | 환기창 위치의 정상 여부 판단 기준 | 부족한 제어기 신호에서 자동 제어·수동 조정 상태의 경계를 판단하는 짧은 명사구로 정리한다. |

