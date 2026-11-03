# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:570416
original SHA-256: 935930259FE143E637180A61F9907A2B1B7D65444BD3199892E4D428F165AC46
candidate SHA-256: 935930259FE143E637180A61F9907A2B1B7D65444BD3199892E4D428F165AC46
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570416_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:570600
original SHA-256: 3F2D4C86600250010FD16B692EDB175FFC6FA607DCC214ADBD865DC91676B5D8
candidate SHA-256: 4AFFABA0AF0A1DA7E6733B97EEBBE057A0A20F5DE3C2E5A5874395369694BDF1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:571459
original SHA-256: F898FFA90944FE675F0C1604B52771E6FBB381BD31067DD707548C0F9DCA55F2
candidate SHA-256: 13B06714006C65D42466F20181E1B226CC9E531F3CD6B8550B64C0A8DBE16188
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:572076
original SHA-256: 69680C94940BF98EDF36B8E2B3C56F0DD7E32170FC64642089730804D2B00D3D
candidate SHA-256: FC85B138CA70BB2041FDF3701D5B492E33D6FE1F6EB70D9862CC3F14A01364E6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:572899
original SHA-256: F83E9BCE729BCE0B97F18F10E88E1732182CC8C5C642F990D6F21242D4766DD5
candidate SHA-256: 6C4808AABD00E3993728E7043BF5623709E0621F5C6ECA682A819744F1CEC483
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

