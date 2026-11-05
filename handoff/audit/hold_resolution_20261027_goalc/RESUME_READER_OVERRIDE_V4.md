# 기존 다섯 역할의 판독기 버전 전환

기존 RESUME_AFTER_STORAGE_ROLE_BINDINGS_20261105_V1.json과 RESUME_NEXT_FIELD_ROLE_BINDINGS_V1.json의 역할·원문·출력 경로 및 금지를 유지한다. 판독기만 새 고정 별칭 `tmp/hold-{c,l,h,j,g}-lossless-v4`로 바꾼다. entry3 F844698C/core3/동일 V4 보호계약/동일 원문·후보 SHA와 protocol V2를 사용하며, scope4 D286EF9F는 기존 scope3의 역할 배정과 같다.

현재 읽던 ID는 기존 판독기로 EOF까지 끝내고 다음 ID부터 새 판독기를 사용한다. 한 ID 안에서 서로 다른 판독기의 part 번호를 섞지 않는다. 원문은 항상 전량 읽으며, 새로운 exact OLD/NEW 표시는 후보 전문과 동등한 무손실 표현이다. 모든 파트와 끝 표식, 양쪽 SHA를 확인한다. 신규 판독기의 각 역할 첫 완독 ID와 part 수는 다음 통상 진행 보고에 적으면 되고 별도 pilot 사본을 만들지 않는다. 그 뒤 기존 전체 배정을 계속한다.

호출 형식은 이전과 같다. C/L은 `bash /home/uranus/tinyLM/tmp/hold-c-lossless-v4 SOURCE_ID pair PART` 또는 l 별칭을 사용한다. H/J/G는 본인 별칭 뒤에 `PAGE SOURCE_ID pair PART`를 준다. KEEP_SOURCE 출력은 새 헤더의 keep_output_absolute를 그대로 쓰고, 후보 그대로는 accept_output_absolute를 쓴다. 동일 TXT 사본을 만들지 않는다.

기존5역할metadata 사전검사·보호ID/타역할 거절·새 별칭의 실제 긴 문서 첫파트 전달을 확인했다. 독립 decoder의 실제6쌍 바이트 복원과21시험이 통과했다. 278626의 원문44187자/후보44171자 쌍은 전달199953바이트50파트에서100973바이트26파트가 됐으며 모든 원문·후보 바이트는 동일하다. 이는 단일 사례의 전달량이며 인간 검토 처리율이나 전체 정제·모델 품질을 뜻하지 않는다. 기존 cache15와166핀은 변경하지 않는다.
