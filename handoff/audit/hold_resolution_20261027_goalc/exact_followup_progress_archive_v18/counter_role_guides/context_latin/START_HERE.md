# 채택 전 독립 원문/선택본문 교차 판독
역할: context_latin; 자기 작성 원문은 배정되지 않았다. 한 TASK는 재개 단위이지 전체 작업량 제한이 아니다.
원문/본문/모든 실제 diff를 끝까지 읽어 독립적으로 완결되는지 판단한다. prior candidate는 자동 후보가 아니라 이미 1차 검토한 선택본문이다.
바이트 동일성은 내용 완결·정제 완료 증명이 아니다. 문서 자체의 빈 주체/인수/표 축, 미완 절, 그림/인용 포인터, 광고·추출 혼입도 확인한다.
유효한 이름·값·관계·조건·부정·시점·불확실성·인용 주체·일반 코드는 보존한다. 원문에 없는 함수/수식/개행/글리프/표 축을 만들지 않는다.
입력은 자기 TASK의 정확 original/candidate/packet 및 ROOT_KNOWN_CONTEXT_FINDINGS_V1.md뿐이다. 다른 역할·다른 세션·보호 자료는 금지다.
출력은 이 자기 폴더의 TXT/MD뿐이다. 코드/JSON/시험/계산/Git/웹/GPU/모델은 금지하며 제공된 고정 읽기 reader만 실행 가능하다.
동일 본문이면 전체 원문을 읽고 TASK의 byte identity 근거를 기록해 중복 본문 표시 생략을 사용한다. 변경 본문은 source/body/diff 전량 판독한다.
packet은2000자의 연속 프레임이다. 물리 경계는 손상이 아니다. 출력 잘림은 지정 reader의 해당 packet만 재호출한다.
후보가 전체로 적절하면 ACCEPT_CANDIDATE와 정확 candidate TXT명. 복사하지 않는다. 교정이 필요하면 REVISE_TEXT와 자기 새 TXT, 원형 hold MD.
새 드래프트는 exact candidate에서 아직 없는 ID_counter_working_v1.txt로 cp --no-clobber한 뒤 아직 리뷰에 선택하기 전까지 좁은 패치로 편집 가능하다.
원형/초기후보/기존 선택/기존 리뷰/역사 기록 덮기·삭제·개명·EOF 바이트 절단·sed 시작끝 범위삭제는 금지다. 리뷰 선택 뒤 working TXT도 고정한다.
review_NNN.md: ID/판정/실제 판독 범위/정확 출력/구체 근거 5열의 해당 TASK 전 행. 최종 전체 diff/EOF를 확인하고 선택한다.
미결 의미만 좁게 총괄에게 질문하고 다른 ID를 계속한다. 명백한 빈 형식/문서LF는 기록하고 스스로 처리한다. 같은 원문을 메타 확인 때문에 재독하지 않는다.
검토 메모를 학습 TXT에 섞지 않는다. 새 무기 제작 세부 등 보호 분류를 발견하면 상세 재작성 없이 metadata 사유만 총괄에게 알리고 다른 ID를 계속한다.
독립 재검토는 신규 1차 고유 원문 수에 더하지 않는다. ROOT·캐시·학습 채택 권한은 없다.
읽기 명령: bash /home/uranus/tinyLM/tmp/hold-l-root12-v1 expanded_train:ID PACKET_NUMBER
추가 기준: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/root12_independent_admission_counter_v1/ROOT_KNOWN_CONTEXT_FINDINGS_V1.md
