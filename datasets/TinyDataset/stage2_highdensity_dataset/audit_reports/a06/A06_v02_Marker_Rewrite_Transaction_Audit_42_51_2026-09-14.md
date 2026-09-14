# A06 v02 표식형 primary 재서술 — transaction 감사 (physical line 42~51)

- source `concept`·`text`와 같은 locator registry `primary` 10개만 함께 변경했다. relations, `other_type`, source 행 순서와 registry의 다른 필드는 보존했다.
- candidate는 7,800행 중 대상 10행만 바꾸고 비대상 byte mismatch 0을 확인했다.
- source v02 SHA-256: `4D3F738EF32C535646EA2BB0F4A9B2122EDDAB0C9BE23868AD896293DBF7BAB6` → `DF12FA874F2A117A1F277B1CF995379A8657F129C3B5308969325F9B3178E00F`.
- registry SHA-256: `22A71110A5CF76300880D60DB26FE732811DDB493E207448F0B23DB5F29FBC4A` → `835750A8228CBAF14887BE27C2E378280D47CC49E9EA3991880383C1FA66D24B`.
- 구조 재확인: source 52파일·7,800 records, registry 7,800 rows, hard error/JSON parse·locator 누락·중복/`concept`↔`primary` mismatch 0. v01 `other_type` text mismatch 25건은 보존 경고다.
- v01 source SHA-256 `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610`은 변경되지 않았다.
- 표식형 primary는 7,582건에서 7,572건으로 줄었다. 전체 재서술 전이므로 A06 전역 자연성·유사도·token 감사와 package/checkpoint projection은 아직 실행하지 않았다.
