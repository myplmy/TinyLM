# v11 중간 저장 준비기의 이름 충돌

실행 chunk `dd3e0e`에서 v11 준비기는 108개 감사 사본과 `EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V11.json`을 만든 뒤 기존 `EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V9.json`에 배타 생성하려 하여 FileExistsError로 종료했다. 중첩 AST 이름 치환의 키/값이 함께 바뀐 것이 원인이다. 기존 파일은 배타 생성으로 보호되어 덮이지 않았다. Git staging/commit은 호출하지 않았다.

실패한 v11과 부분 사본108개/색인은 삭제·덮기·복원하지 않는다. v11의 large index와 save manifest는 생성되지 않았으며 이 실행을 저장 완료로 계산하지 않는다. chunk `2692f7`에서 세 경로와 부분 사본 수를 확인했다.

후속 v12는 기존 v7 준비기를 한 번만 변환해 새 이름을 고정한다. 기존 guard의 명시 경로·부모 HEAD·빈 index·전체 blob 검산을 유지한다. 이번 중간 저장과 무관하게 다섯 역할과 전체 정제는 계속 수행한다.
