# 회수 본문 8건의 실제 값·코드 보존 판정

총괄은 `authored_body_integrity_v1.json`의 8개 신호에 대해 지정 원문/본문 SHA, 실제 diff와 독립 전문 판독을 대조했다. 이 문서는 정확 본문 선택의 근거이며 실제 캐시 생성·goal 완료·외부 사실 검증이나 모델 품질 판정이 아니다.

| 원문 ID | 선택 | 실제 근거와 한계 |
|---|---|---|
| expanded_train:383689 | historical_review/integrity_counter_v1의 v2 본문 | rowspan의 회차·조를 각 행에 전개한 숫자 반복은 새 값이 아니다. 빠진 신지훈 패자부활전 행은 원문 순서·공연·트레이닝·결과 관계로 복구했다. 실제 값 표가 없는 시청률 안내만 별도 보류했다. |
| expanded_train:36061 | 원문 KEEP | 원문과 후보가 같은 바이트다. 장 끝의 `~~~~ end chapter ~~~~~`는 실제 프로그램이 아니며, 귀속된 보호자 경험담·직접 인용·자료 URL은 그대로 보존한다. 원래 fence 탐지의 미종결 신호를 전역 해제하지 않는다. |
| expanded_train:4003 | context_hangul/integrity_counter_v1의 v5 본문 | 사전 팝업이라도 완결된 정의·원래 수치와 발음 전사를 보존하도록 v3을 거부했다. v5는 기사/저자 약력 뒤로 정의를 분리해 기사 문장 흐름도 회복했다. Human genetics와 identical twins의 실제 미완 두 조각은 보류한다. 발음 전사를 복원한 뒤 원래 code_guard도 True다. |
| expanded_train:8455 | context_hangul/strict_failure_text_repair_v1의 v3 본문 | 검색 UI의 backtick 버튼 표시는 프로그램이 아니다. 정의·COBOL85 키워드·원래 URL과 학술지 서지를 보존한다. v2에서 완결 예시까지 잘린 것을 root diff로 확인해 arts/criminal justice를 v3에서 복구했고 끊긴 foundati 꼬리만 분리했다. |
| expanded_train:1709 | readback에 고정된 legacy_rendered_v3 본문 | `above6`→`above 6`은 같은 원래 숫자의 공백 경계다. 손상 전제를 쓰는 세 문장만 실제 문맥으로 분리했으며, 독립 저자 주장·수량·조건·링크를 보존한다. 저자의 과학적 주장을 검증한 것이 아니다. |
| expanded_train:6175 | readback에 고정된 legacy_rendered_v3 본문 | `Table4-1`→`Table 4-1` 및 식별자 앞 공백 변화다. compress(), MAX_PACKET_LENGTH, 파일명·수량·버전·실패와 분할 조건은 보존한다. 누락된 표 열/오프셋을 새로 만들지 않는다. |
| expanded_train:8121 | readback에 고정된 legacy_rendered_v3 본문 | 원문 발음 전사 사이의 backtick이 서로 다른 사전 설명을 가로질러 inline code로 잡혔으나 실제 프로그램이 아니다. 손상 저자열에서 Jing H라는 이름을 만들어 낸 옛 안은 거부했고, 새 본문은 그 필드만 보류하며 논문 본문·byline·독립 사전 정의·남은 서지를 보존한다. |
| expanded_train:5416 | readback에 고정된 legacy_rendered_v3 본문 | `of0.9%`→`of 0.9%`의 공백만 다르다. 원문 값·단위·처치 조건을 보존하며 현재 임상 지침으로 추천하거나 사실 검증한 것이 아니다. |

숫자 Counter 차이와 코드 탐지 False를 각각 값 창작·프로그램 손실의 확정 판정으로 읽지 않는다. 반대로 정렬된 문자·코드 검사가 True라고 누락된 사실이 없다는 뜻도 아니다. 선택한 본문·원문·판독 근거는 별도 JSON의 정확 SHA로 고정하며, 다른 본문 버전에 이 예외를 빌려 주지 않는다.

원래 일곱 literal 예외에 더해 실제 프로그램이 아닌 세 쌍(36061/8455/8121)만 추가 검토할 수 있다. Unicode 보호는 그대로이며 원래 프로그램 세그먼트를 제거하는 일반 허용 규칙은 만들지 않는다.
