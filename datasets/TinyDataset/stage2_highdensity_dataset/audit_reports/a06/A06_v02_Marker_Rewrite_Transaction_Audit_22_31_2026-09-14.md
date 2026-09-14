# A06 v02 표식형 primary 재서술 — transaction 감사 (physical line 22~31)

## 반영 결과

- source v02 physical line 22~31의 `concept`과 `text`를 직접 재서술했다.
- 같은 locator의 A06 registry 10행에서는 `primary`만 동기화했다. `definition`, `provenance_*`, `review_status` 및 locator는 보존했다.
- registry candidate는 7,800행·target 10행이며, 비대상 7,790행의 body·line terminator byte mismatch는 0이다.
- source v02 SHA-256은 `159CB88766D2C066F86E5D84349D7ACF6C6E804F88AD7469CE14CCE441C1C449`에서 `3AA1D22764C0A794517278DF25A461D634D2DCFA25078BC09A8722F5DE5EB3BD`로, registry SHA-256은 `92CBBEDB146E5F55564823B3F309D3928B15EC99E2659639F5075A53B7A47DF1`에서 `BFFB72A88E1227A62F2635826E03C8E664C33174DC9EFCB07393B4763551A955`로 바뀌었다.
- v01 source SHA-256 `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610`은 그대로다.

## 구조 재확인

- A06 source 52파일·7,800 records, registry 7,800 JSONL rows.
- UTF-8/PSV header·열 수/공백·제어문자/빈 필드/primary literal/exact 중복/relations 통제어휘·cardinality·내부중복 오류는 0.
- registry JSON parse, locator 누락·중복, `concept`↔`primary` mismatch는 0.
- v01의 보존된 `other_type` text literal 불일치 25건은 기존 legacy warning이며 이번 수정 대상이 아니다.
- 구조 판정은 `PASS_WITH_LEGACY_WARNING`이다.

## 자연성 판정의 경계

표식형 primary는 7,602건에서 7,592건으로 줄었다. 그러나 v02~v52 전체의 행별 재서술이 끝나기 전에는 TF-IDF/Jaccard·조사·token 평균을 다시 전수 판정하지 않는다. 따라서 이번 묶음의 자연성 최종 판정·package/checkpoint projection은 모두 아직 `NOT_RUN`이다.

원복용 source/registry 원문과 의미 근거는 [사전 변경계획](A06_v02_Marker_Rewrite_Prechange_Plan_22_31_2026-09-14.md)에 보존했다. registry 원복본은 `A06_registry_before_v02_marker_rewrite_22_31_2026-09-14.jsonl`이다.
