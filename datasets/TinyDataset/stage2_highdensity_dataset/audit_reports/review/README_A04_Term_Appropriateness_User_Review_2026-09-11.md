# Stage2 A04 용어 적합성 사용자 검토표

대상 파일: `TinyLM_Stage2_A04_Term_Appropriateness_User_Review_2026-09-11.tsv`

이 표는 A04 원본 10,350개 레코드 중, primary의 qualifier에 조사·연결어·절단 어근·동사 어간이 남았거나 사용자가 지목한 합성어가 **개념명으로 자연스럽지 않을 수 있는** 69개 후보만 뽑은 것이다. 자동 판정은 오류 확정이 아니라 사용자 검토 대상 선별이다.

## 입력 방법

- 각 데이터 행의 **마지막 열** `user_decision_Y_or_N`의 `PENDING`을 정확히 `Y` 또는 `N`으로 바꾼다.
- `Y`: 해당 레코드는 primary와 text를 함께 재작성해야 함.
- `N`: 현재 표현을 유지해도 됨.
- 아직 판단하지 않은 행은 `PENDING`으로 남긴다.
- locator, primary, term_under_review, relations, text 열은 수정하지 않는다. 행 순서를 바꾸지 않는다.

반환 후에는 `Y` 행만 현재 원본의 locator·primary·텍스트를 다시 대조한 뒤, 레코드별 패치로 수정하고 전수 감사를 재실행한다. `N`이나 `PENDING`을 근거로 한 자동 수정은 하지 않는다.

## 기준 스냅샷

- 검토표 생성 시 A04 독립 구조 감사 source-set SHA-256: `691c7e563bd7ea39a9f03c884eb1fd0d84b3f09cdaa90311253b44f63ebd7d7e`
- review rows: 69
- source records: 10,350
