# 전량 재개 중 실패·정정 추가 기록 v10

이 문서는 앞선 v1–v9를 보존한 후속 기록이다. 실패를 성공으로 덮지 않는다.

- metrics writer v1은 core verified.json에 없는 goal_complete를 직접 인덱싱해 KeyError로 종료했다. 캐시 생성/검증 실패가 아니라 보고 코드의 필드 소유권 오류다. 출력 보고서 생성 전이었다. v2는 필드 부재를 ABSENT_NOT_A_GOAL_STATUS로 분리하고 실제 partial/restricted/baseline 증거의 명시 false를 별도로 확인했다. 새 실계측 JSON과 한국어 보고서가 생성됐다. 캐시는 재생성하지 않았다.
- 재개 첫 읽기에서 python 별칭을 사용해 command not found(exit127)가 났다. 파일 판독/변경이 없었고 승인된 tlm_torch의 절대 Python 경로로 수정했다.
- 역할 폴더 아래 .manifest.json을 추정해 읽으려다 FileNotFoundError가 났다. 실제 그룹 루트의 manifest.json을 확인해 정확한 입력을 회수했다. 실패 호출은 전문 판독 근거가 아니다.
- 공개 조정문 추가 명령에 literal backslash-n을 넣어 PreToolUse 역슬래시 보호 훅이 셸 실행 전에 거부했다. 자동 승인 리뷰 거절은 아니다. 실제 개행 조립에 chr(10)을 사용해 같은 공개 문서만 append했다. 기존 내용 변경이나 우회 실행은 없다.
- literal snapshot7은 historical review_026_v3의 다섯 ID가 TASK026 소유가 아니라는 것을 검출했다. 잘못된 행은 유효 증거에서 제외했고 해당 역할에 실제 TASK별 새 리뷰를 요청했다. errors0은 잘못된 과거 행 부재를 뜻하지 않는다. invalid_task_rows5를 별도로 보존한다.
- 동일 입력의 후보 중간 패킷 생략을 후보 전문의 손상으로 오인한 질문은 실제 바이트/전체 frame 재구성과 ROOT_IDENTITY_PACKET_GAPS_CLARIFICATION_V1에 근거해 정정했다. 실제 도구 출력잘림은 별도로 재판독하며 같은 사유로 덮지 않는다.
- Luna가 보고한 경로 오타·없는 ROOT_CAT_COMMANDS 추정·다른 ID sidecar 혼입·sed 구문 혼입/오삭제 초안은 각 자기 오류 메모와 비선택 초안을 보존하고 새 버전/정확 리뷰로 회수 중이다. 모든 과거 호출의 비접근0이나 모든 미완의 정정 완료를 주장하지 않는다.

cache3의 실제 생성0/독립consumer0은 별도 실행 증거에 있다. 위 보고·경로·리뷰 연결 실패를 모델 품질/전체 정제 완료나 원문 불량으로 바꾸지 않는다. 전체 goal은 active다.
