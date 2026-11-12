# validation:3482 — 누락 Java 서버 예제 HOLD

- 원형: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_literal_full_counter_v1/inputs/validation_3482_original.txt`
- 원형 SHA-256: `5C8F15169532768418C8D198816AA23D22F49D5AE41766CD881A6B9F7105153A`
- 부분 정제 본문: `validation_3482_root12_working_task309_v1.txt`
- 판독: 고정 V6 reader, 원문 전체 + 무손실 후보 표현 전체, EXACT_PATCH_WITH_OLD_AND_NEW, 2/2 parts, 양 SHA·보호 사전검사 및 SOURCE_DATA_VIEW_EOF 확인.
- HOLD 앵커: `Here follows an example of a very simple java socket connector`부터 `If you have some basic Java knowledge`까지의 불완전 서버 코드와 직접 결속된 도입/마무리 문장.
- 사유: 서버 코드에 선언·블록·인수 경계가 빠져 있어 실행 가능한 형태로 복원하지 않았다. 다른 독립적인 클라이언트 개요와 Java 서버 설명 목록은 본문에 보존했다.
- 원형 코드나 packet을 sidecar에 복사하지 않았다.
