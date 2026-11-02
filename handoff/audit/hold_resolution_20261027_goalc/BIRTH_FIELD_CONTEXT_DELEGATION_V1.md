# 생년 필드 부분 복구 후보의 전량 문맥 판독 위임

`birth_field_native_proof_v1/complete.json`의 실제 원문774건 검산에서753개 고유 원문·1,135위치가 기존 검사까지 통과했다. 18건은 다른 내용 사유가 남고3건은 원문 역할 증명이 성립하지 않아 해제하지 않는다. 이753건은 자동/원문 검사 통과 후보이며 아직 캐시 채택은0이다.

사례 몇 개로 전량의 의미 보존을 대신하지 않기 위해753건 전부를 다섯 Luna/max 역할에 배정한다. `birth_field_native_counter_v1/manifest.json`이 정확 ID·원문/후보 SHA·구간·역할·TASK를 소유한다. 역할은 `context_controls`, `context_latin`, `context_hangul`, `historical_review`, `legacy_review`이며 각 역할 출력은 `data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/<role>/birth_field_native_counter_v1/`의 새 TXT/MD뿐이다.

허용 읽기는 자기 START/TASK/READING_VIEWS, 그 TASK에 지정한 원문·후보·diff 및 명시 경계를 둔 읽기 패킷과 모든 순서 조각이다. 다른 역할 출력, 이전 작성자 리뷰, 코드·정책·증명 JSON은 입력으로 주지 않는다. 원문의 실제 두 연도와 월일·사망일·다른 수치·조건, 남은 문맥의 독립성을 직접 판단한다. 후보가 적절하면 정확 지정 후보를 수용하고, 오삭제/잘못된 연결이 있으면 새 전체 TXT와 별도 보류 MD를 저장한다. 어느 생년이 맞는지는 추정하지 않는다.

코드/시험/통계/해시/Python/모델/GPU/Git/웹/설치/보호 TinyDataset/타 세션/공유원장 접근은 금지한다. 좁은 텍스트 읽기와 새 TXT/MD 편집만 허용한다. 모든 입력을 실제 EOF까지 읽고 미판독·출력 잘림은 완료로 세지 않는다. root가 모든 저장 결과의 SHA·TASK·전체 diff·최신 충돌을 검산하고 중재한다. 위임은 코드나 전체 캐시 채택 권한을 확대하지 않는다.
