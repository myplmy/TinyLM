# Parent ledger의 중첩 출처 메타데이터 처리

ROOT32/roster23용 opaque join 첫 시도는 parent ledger 한 행의 `original_text_sha256` 원시 정규식 일치가 여러 개인 것을 거절해 출력 전에 종료했다. 이 검사는 top-level identity와 중첩 provenance를 구분하지 않았다. 원형·후보 TXT를 열거나 body 값을 decode한 실패는 아니다. 실패 로그를 보존하며 출력 계약·metadata 디렉터리는 아직 생성하지 않았다.

| 안 | 장단점 |
|---|---|
| A. 행 전체 JSON decode | 구현은 짧으나 보류 본문 비해독 경계를 위반하므로 제외한다 |
| B. 첫 정규식 일치만 신뢰 | 빠르지만 중첩 key의 순서에 따라 다른 출처를 고를 수 있어 제외한다 |
| C. 원시 일치는 사전 필터로만 쓰고 기존 byte projector로 top-level identity 확인 | 기존 비해독 경계를 재사용하고 중첩 출처를 허용하면서 실제 parent HOLD 조건을 엄격히 확인한다 |

수행은 C다. `opaque_parent_projection_v1.py`, 이전 generator를 해시로 재사용하는 v2 wrapper와 작은 CPU 회귀만 신설한다. 사용자 objective의 관련 전처리 코드·시험 승인 범위다. 실제 원문·캐시·모델·환경 파일 변경은 없다.

영향: 코드 호출부는 opaque generator의 parent ledger 선택 한 곳이다. HOLD 수량·원문 SHA·구간·parent decision·shard/전체 검산은 기존대로 유지한다. 데이터 형식·학습 조건·의미 판정은 바꾸지 않는다. 중첩 SHA, escaped body, top-level 불일치, 선택 parent의 비HOLD를 시험한다. WIP와 새 시도 로그에 실제 종료를 반영하며 실험 기준표/METHODS/COMPASS 변경은 없다. 이 수정은 새 전체 캐시 성공이나 속도 인과 증거가 아니다.
