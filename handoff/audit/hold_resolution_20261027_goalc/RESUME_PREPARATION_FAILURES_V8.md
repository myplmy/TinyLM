# 계속 정제 중 오류·정정 이력 V8

이전 V7 및 각 원형 파일·실패 출력·초안·불선택 리뷰를 보존한다. 이 문서는 실제 확인과 보조 역할의 자기 보고를 구분한다. 전체 goal은 active이며 중간 저장/정적 검사를 완료·일시중지로 처리하지 않는다.

1. ROOT11 preview1은 기존 ROOT10 일부 선택의 original_paths를 압축 중 누락했다. 새 guard v4가 KeyError: original로 중단했다. preview1/producer1/v4는 보존하고, preview2/producer2에서 실제 원문 경로를 이어 guard v5의 fallback으로 보정했다. 캐시 채택은0이다.
2. guard v5는 preview2의 본문 UTF-8 decode 중 unexpected end of data로 중단했다. Luna controls가 보고한 TASK085 말미 바이트 제거 손상과 시점상 겹치지만 정확 대상은 v6의 개별 기록으로 확인한다. controls는 세 working_v1과 옛 리뷰를 보존하고 원형 base에서 새 v2를 복구했다고 보고했다. 이 이전 스냅샷을 최신 복구본으로 간주하지 않는다.
3. 새 guard v6는 손상 본문의 ID/SHA/정확 decode 구간을 실패로 기록하고 다른 본문 검사도 이어간다. 실패 항목을 자동 통과시키지 않는다. 이후 스냅샷과 선택안에서 실제 복구본을 재검산해야 한다.
4. 동일성 판독 producer1은 역할별 V1 MD를 생성한 뒤 마지막 JSON 직렬화에서 set 타입으로 실패했다. 해당 파일들은 미채택 이력으로 보존한다. producer2가 TASK ID를 정렬한 list로 직렬화하고 전량 다시 검증해 V2 MD360개/완료 증명을 썼다. 실제 바이트 동일1675건, 원문 전문/최종diff 필수8035패킷, 중복 후보만3999패킷, 비동일118건이다. helper11시험은 실제 종료0이다.
5. root의 guard v4 생성 시도는 명령 문자열의 역슬래시 n 때문에 PreToolUse 훅이 쓰기 전에 차단했다. 실제 여러 줄 문자열로 작성해 해결했다. 이전 checkpoint2 builder와 legacy1137652의 같은 훅 자기 보고도 보존한다. 자동 승인 심사 거부로 보고하지 않는다.
6. snapshot13에서 Latin 출생525187은 새 본문/sidecar/review_070_v2의 실제 연결이 확인돼 기계결합 오류가0이 됐다. literal TASK001은 실제5건 중1행만 저장돼 있었으며 root가 actual TASK/리뷰로 누락4건을 확인했다. Luna가 누락 원문을 전량 읽고 새5행review_001_v2로 보완했다.
7. root가1250221 원문 전문에서 없는3메서드 목록과 주체 없는It 설명을 확인했다. candidate 동일을 근거로 한 ACCEPT를 철회하고, 명명된notify의 독립 문장은 유지한 새본문/sidecar/review013_v3로 중재했다. Latin의 이전001–013 수용 결과도 같은 경계를 회고검토하도록 지시했다.
8. historical의104112를Cylinder로 보고한 초기 메시지는 실제POSIX sem_open 입력과 달랐다. root는 잘못된 보고를 증거로 쓰지 않도록 지시했고, Luna가 실제 입력을 다시 대조해104112/1042166을 구별한 새본문/리뷰로 정정했다고 보고했다. 1044095 v1의OS문자 전사 실수도 v2에서 교정했다고 보고했다. 이 과거 보고를 독립 검증 성공으로 세지 않는다.
9. Hangul은1326255 패킷과원문이 서로 다른 두문구라고 보고했다. root가 실제 SHA와5패킷 전체 재구성을 다시 검증해 현재 원문/후보/패킷 모두 `One Workbook to Multiple Excel, PDF or CSV Files`임을 확인했다. Luna가 정확명령으로 재판독 후 새본문/sidecar v3를 작성했다. 잘못된 전사 초안v1/v2는 보존한다.
10. 역할별 No such file/잘못된 wrapper·입력 접두어·Python 실행파일을 script로 넘긴 오류·불필요 piece3의 범위 거절·금지 dummy 경로 추가는 자기 보고 및 관련 원형 note를 보존한다. 실패 반환을 문서 내용 판독으로 계산하지 않는다. 과거의 모든 경로 접근이0이었다고 주장하지 않고 타 세션 사적 로그를 조사하지 않는다. controls의 과거 unscoped rg 접근범위 미확인도 계속 유지한다.
11. 새 partition helper11시험과 cache v3 보호 runtime 초기화는 각각 실제0이다. 초기화는91개 경로 pin과 검토 비채택38개의 연결을 확인한 범위이며 실제 cache build/독립 consumer는 NOT_RUN이다. 같은 의미로 전체130개 runtime 실행이나 본문 품질 통과로 확대하지 않는다.
12. snapshot14의 현재 선택에 기계결합 오류0이라고 한 것은 파일경로/행 연결 검사 범위다. Unicode·숫자·코드·의미 검사가 모두 통과했다는 뜻이 아니며, 위 UTF-8 실패가 이 구분을 뒷받침한다.

어떤 수정본도 원문/이전 캐시를 덮어쓰지 않는다. 현재 공식 cache_reviewed_partial_v2의H115526과 학습 금지는 그대로이며 ROOT11은 아직 preview다.
