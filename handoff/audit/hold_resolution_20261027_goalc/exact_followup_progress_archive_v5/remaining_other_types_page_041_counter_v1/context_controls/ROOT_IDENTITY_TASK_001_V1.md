# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:501586
original SHA-256: 7F0846A925719CAF5E584BBA617D3602314E48666DE61AB3AD458F756EB3AD99
candidate SHA-256: 7F0846A925719CAF5E584BBA617D3602314E48666DE61AB3AD458F756EB3AD99
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_041_packet_v1.py --source-id expanded_train:501586 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_041_packet_v1.py --source-id expanded_train:501586 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:501639
original SHA-256: E575F5FD6E3B946FD794DAC2D74783D4139DC8F24B6DA011BCE73A10DA9626AF
candidate SHA-256: A036C466C8F8FEDFBDBE32326FAAD84AFED85105A32DEA72F222BE01A68C8628
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:501771
original SHA-256: 1F5FAE7F44429FA1E1F6FF7A246AA2F7342158D9150762B69672C48B7A240885
candidate SHA-256: 3AB180424C609796F3B85D96A982A9DA9F3A7E0ADF01C8616D57A6A45D4F783B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:501923
original SHA-256: 9050BCE05E4E82DF2452D4513904286152205167EB6D556EDA0F596B15DFD5BB
candidate SHA-256: F26A9E8E4EAA56A8B5B3576E58D57A972082A247E1D34FF030841E1C0A0959FF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:502205
original SHA-256: 14661A56977F24314C014B864D4A9F10856F26E36949323CFC1F694176FD76B7
candidate SHA-256: 340BBF8E0E4C7C4CB6E9990CE0D18C381EB2899E17E571CBA9E6F1D82E95AB50
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

