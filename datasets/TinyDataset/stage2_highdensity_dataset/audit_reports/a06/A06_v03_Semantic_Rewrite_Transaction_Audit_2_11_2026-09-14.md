# A06 v03 의미·자연성 재서술 — transaction 감사 (physical line 2~11)

- 변경 범위는 v03 source의 `concept`·`text` 10행과 같은 locator의 registry `primary` 10개뿐이다. relations, `other_type`, source·registry 행 순서, registry의 다른 필드는 보존했다.
- source v03 SHA-256: `663BC5284A20B62B9940B640B4D663CB8F6A688DC183A7D215C88E86FF9D9EAF` → `2D246C5335FFD80F81427A00C8BAA811EA7E2EAA04265440CDEB5CB22ECACC29`.
- registry SHA-256: `15899E70972E512B1F78878EA56A2DC7173AC5296750A08EFC7C818F3049B3DD` → `6EC43D9F77CC5891661A22A0C2B158F4E554907EDF7E303DA747AD53D0D68EE5`.
- registry candidate preflight는 7,800행·대상 10행·비대상 7,790행 byte mismatch 0·대상 non-primary field 변화 0을 확인했다. 원복 backup은 `A06_registry_before_v03_semantic_rewrite_2_11_2026-09-14.jsonl`이다.
- 재감사 결과: 52 source files·7,800 records·registry 7,800 rows, UTF-8/PSV·registry JSON parse, 150-record 파일 수, primary literal, exact concept/text 중복, controlled relations·2~5 cardinality·내부 중복, `other_type` 규칙, locator 누락·중복·`concept`↔`primary` 불일치는 모두 0이다. 구조 판정은 `PASS`다.
- v03:2~11의 semantic rewrite queue는 0이다. 직접 검토 기준의 관측 계기·판단 주체·연결 보류/구분·오판 방지 결과를 각 행에 넣었고, 작성 표식과 번호 접미사는 제거했다.
- 전체 A06 의미 판정은 아직 `HOLD_REWRITE_QUEUE_PRESENT`다. 잔여 queue 7,658건(v03 12~151은 140건)과 전역 고유사도는 후속 v03~v52 재서술 대상이며, 이번 10행 구조 통과를 전체 자연성 PASS로 해석하지 않는다.
- 재감사 참고 수치: 동일 relation-set 1,046,052 pair 중 word Jaccard ≥0.75는 158,721, word TF-IDF cosine ≥0.85는 150,182이며 각각 최대값은 1이다. `primary+은/는` 시작은 103/7,800=`1.3205%`로 advisory 범위다.
- v01 source SHA-256 `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610`은 보존했다. package `train/val`, manifest, 중앙 원장, checkpoint, 공용 감사기, 다른 영역 source는 수정하지 않았다.

다음 재개점: v03 physical line 12~21의 사전 변경계획과 10-locator 직접 재서술.
