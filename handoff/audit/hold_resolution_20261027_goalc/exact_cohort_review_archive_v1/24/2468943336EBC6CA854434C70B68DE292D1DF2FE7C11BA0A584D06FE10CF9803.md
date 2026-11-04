# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:214752
original SHA-256: 032903E8A9C86D1E3EA12A64683039A9AB22F94D7EFA7BA73A9F767FC3378F48
candidate SHA-256: 6C02FCDFE24EFDE079F1927216AC288B8E0E4E5F5CC0389B3BA66EF52527EE80
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:214771
original SHA-256: C86E71452A52BBA35AD97A250F0C27AFD8C40FA34BE974136BB0BA78930CC7A5
candidate SHA-256: 2BD8371DA64B668C16C7456E9404E89F896A963B34B872076C44D842AB2B9852
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:214832
original SHA-256: 2CFEA55E4B75ABF380EBE92C615DE4E07FE4B3E0061EAC933EBEECA84BEF80C5
candidate SHA-256: 680BC71C67D6BCFE622BB77469B4A180A2B7BC6CCF2376439F0230ACF5A0BA24
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:215038
original SHA-256: 3237CD9674CB26890CEA4F81391E19A3926D75F876172300C56C4614232387D4
candidate SHA-256: C6C730AA2F5D024DE720260511F9AEE117A32832BA8B42D9A0304F5B12CF200B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:215163
original SHA-256: 6C13394EE3C7546542D60177C16D8C664A75863577FBF0C42D3D7CC0A3B52053
candidate SHA-256: 6C13394EE3C7546542D60177C16D8C664A75863577FBF0C42D3D7CC0A3B52053
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_215163_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

