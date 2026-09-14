# A06 의미·자연성 품질 Gate (2026-09-14)

## 목적과 범위

이 gate는 Stage2 A06 `relational_composition` source v01~v52의 구조 통과와 한국어 의미 품질을 분리한다. 대상은 legacy PSV source와 A06 전용 term registry뿐이다. package `train/val`, manifest, 중앙 원장, checkpoint, 공용 감사기와 다른 영역은 범위 밖이다.

## 행별 재서술 기준

재서술할 문장은 선행 문맥 없이 다음을 드러낸다.

1. 구별 가능한 대상 둘 이상 또는 대상과 기록·판정 주체
2. 관찰값·상태·충돌·결측 가운데 하나의 구체적 계기
3. 누가 무엇을 보류·선택·분리·전환하는지의 판단
4. 그 판단이 무엇을 보존·제한·방지하는지의 결과 또는 경계

`기본 경로`, `예외 목록`, `일부 조치`, `두 관계`, `한쪽`, `나머지 항목`처럼 대상이 문장 안에서 밝혀지지 않는 표현은 단독 설명으로 쓰지 않는다. primary는 실제 명사구여야 하며, `— 연결 확인`, `— 독립 확인` 같은 작성 표식, 번호 접미사, 절단 어근, 부자연스러운 동사어간 합성은 금지한다.

## 감사기 판정

`tools/a06/audit_a06_semantic_quality.js`는 source를 수정하지 않는다.

- `REWRITE_REQUIRED`: 대시 표식·번호 접미사·인접 반복 또는 반복된 일반론 골격처럼 명백한 오류 후보
- `SEMANTIC_REVIEW_REQUIRED`: 불투명한 지시어, 사실 사슬 단서 부족, relations 단서 부족 등 문장별 의미 검토가 필요한 후보
- `PACKAGE_PROJECTION_HOLD`: v01처럼 package projection이 존재해 source만 고치면 불일치하는 후보
- `PASS_CANDIDATE`: 결정적 신호가 없을 뿐, 사람 또는 LLM의 자연성 확인이 아직 필요한 행

동일 relation-set 안의 단어 Jaccard 및 word TF-IDF cosine, primary 제거 뒤 동일 skeleton, `primary+은/는` 시작 비율, 관계 단서 분포를 함께 보고한다. `primary+은/는`은 30% 초과면 review, 45% 초과면 diversity HOLD다.

## 한계와 수정 절차

PSV 자체는 외부 운영 기록이 아니라 학습용 구성 시나리오다. 감사기는 사실의 진위를 증명하지 못하며, 한국어 자연성도 자동 PASS로 선언하지 않는다. 확정 오류만 행별로 직접 재서술한다. primary 변경은 동일 `source_file + source_line`의 A06 registry `primary`만 함께 갱신하고, registry 전체 재직렬화·source 전체 재직렬화·전역 치환을 하지 않는다. 수정 전후 SHA-256·locator·비대상 바이트 보존을 기록한다.
