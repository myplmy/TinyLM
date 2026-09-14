# A06 v02 표식형 primary 재서술 — transaction 감사 (physical line 32~41)

- source v02 10행의 `concept`·`text`와 같은 locator registry 10행의 `primary`를 같이 변경했다. relations, `other_type`, source 순서 및 registry의 다른 필드는 보존했다.
- registry candidate: 7,800행, target 10행, 비대상 7,790행 byte mismatch 0, target non-primary field change 0.
- source v02 SHA-256: `3AA1D22764C0A794517278DF25A461D634D2DCFA25078BC09A8722F5DE5EB3BD` → `4D3F738EF32C535646EA2BB0F4A9B2122EDDAB0C9BE23868AD896293DBF7BAB6`.
- registry SHA-256: `BFFB72A88E1227A62F2635826E03C8E664C33174DC9EFCB07393B4763551A955` → `22A71110A5CF76300880D60DB26FE732811DDB493E207448F0B23DB5F29FBC4A`.
- 사후 구조 확인: 52 source files·7,800 records·7,800 registry rows, hard errors/registry JSON parse/duplicate·missing locator/`concept`↔`primary` mismatch 0. v01 legacy `other_type` text mismatch 25건만 보존 경고로 남아 있다.
- v01 SHA-256 `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610`은 변경되지 않았다. 표식형 primary는 7,592건에서 7,582건으로 줄었다.
- 전체 A06 재서술 완료 전이므로 TF-IDF/Jaccard·조사·token 평균의 전수 자연성 판정과 package/checkpoint projection은 실행하지 않았다.
