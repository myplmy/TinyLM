# literal 네 역할의 고정 읽기 도구 추가

field의 exact 사본과 별도로 literal에서는 _original_ 접두 등 filename 재조합 오류가 반복됐다. 실제 source/pin 파일 부재로 판단하지 않고 고정 reader의 source-id/packet만 선택하는 읽기 예외를 추가한다. 실제 텍스트 정제·새 TXT/MD 작성은 Luna만 담당한다.

| 방식 | 영향/비용 | 판단 |
|---|---|---|
| 기존 긴 경로만 다시 안내 | 새코드 없음, 같은 추정 오류 반복 | 기존경로도 유효 |
| 여러 잘못 추정한 이름으로 사본을 계속 추가 | 디스크/이름 중복·추적 혼동 | 미적용 |
| 이미 검증된 scoped_packet_reader를 역할별 고정registry/CLI로 재사용 | 작은 설정/명령MD, 범위검사 재사용 | 적용 |

새 audit registry/동일 helper wrapper와 자기 literal의 새 ROOT 명령 MD만 만든다. 원문/후보/packet·기존 역할 출력은 변경하지 않는다. ID/SHA 보호 경계를 먼저 검사하며 다른 역할 ID 거부·실제 경계 읽기·CLI 종료0을 확인한다. 코딩/시험/통계/해시/웹/Git/모델/GPU 권한을 Luna에 주는 것이 아니라 이 정확 readonly tool 실행만 허용한다. 새 파일은20MB미만이고 대량본문을 Git에 넣지 않는다. static/실제읽기도구 확인과 의미수용·캐시채택은 다르다.
