# A06 v02 표식형 primary 재서술 — transaction 감사 (physical line 52~61)

- source의 `concept`·`text`와 같은 registry locator의 `primary` 10개만 변경했다. relations, `other_type`, 행 순서와 registry의 다른 필드는 그대로다.
- registry candidate는 target 10행만 변경했으며 비대상 7,790행의 byte mismatch는 0이다.
- source v02 SHA-256: `DF12FA874F2A117A1F277B1CF995379A8657F129C3B5308969325F9B3178E00F` → `F7928BA8311BA1249C7520186F330E062EE1BB7F57F74C124BCEAE55C669D3BE`.
- registry SHA-256: `835750A8228CBAF14887BE27C2E378280D47CC49E9EA3991880383C1FA66D24B` → `46F7BAC980C0C09F1E3F88B7524EF5F59435F84D2CCB3C9012F2D4D34CE98D1C`.
- A06 구조 대조: 52 source files·7,800 records·7,800 registry rows, hard errors/registry parse·locator 누락·중복/`concept`↔`primary` mismatch 0. v01 legacy `other_type` text mismatch 25건은 보존 경고다.
- v01 source SHA-256 `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610`은 보존됐다. 표식형 primary는 7,572건에서 7,562건으로 줄었다.
- 전역 자연성·유사도·조사·token 및 package/checkpoint 판정은 A06 전체 재서술 완료 전이므로 아직 실행하지 않았다.
