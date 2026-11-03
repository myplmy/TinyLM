# expanded_train:216754 — 원형 보류

원문에서 직접 대상이 빠진 다음 두 부분만 보류한다.

- `So when we send a POST request we send a json encoded body like:` — 이어질 JSON 본문이 원문에 없다. 보이는 PNG data URI 예시를 이 누락된 POST 본문이라고 단정하지 않는다.
- `( .gif in this case)`가 아니라 원문 그대로 `(.gif in this case)` — PNG 접두 예시와 별개로 일반 형식을 설명하는 문장에 붙은 GIF 한정은 그 예시 본문이 없어 확인할 수 없다. GIF→PNG로 고치거나 payload를 만들지 않는다.

재작성 본문은 독립적으로 완결된 POST JSON body 언급, 표시된 PNG 예시, data URI의 형식·base64 구성 설명, 파일 확장자 추출, UUID 파일명, 디코딩·저장 및 URL 응답 설명을 보존한다. 부재한 요청 본문 내용이나 이미지 형식의 대상을 추정하지 않는다.
