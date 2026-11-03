# 재개 실패·정정 추가 기록 v11

v1–v10을 보존한 후속 기록이다. 실패/미판독을 실제 성공으로 바꾸지 않는다.

- 이전 큰 선택 JSON에서 일반적인 legacy 경로 구절까지 함께 검색해 필요 이상 출력이 반환되고 도구에서 잘렸다. 해당 전체 결과를 읽었다고 주장하지 않는다. 이후 exact ID/특정 파일의 필요한 metadata 필드만 읽는 방식으로 제한했다.
- snapshot records_000.json을 JSONL로 가정해 행별 json.loads를 호출했고 JSONDecodeError가 났다. 실제 배열 JSON을 통째 로드해 정확 source ID를 필터링하는 것으로 교정했다. 이 실패는 본문 판독/변경이 아니다.
- 새 snapshot의 모든 상태에 review가 있다고 가정한 metadata 조회가 KeyError로 끝났다. 미저장/다른 상태에 독립 review 필드가 없을 수 있으며 후속은 존재 여부를 구분한다. 새로 보고하지 않은 질문까지 확인 완료로 올리지 않는다.
- field 담당자가 page001의 첫TASK를 마친 뒤 page002로 넘어간 사실을 발견했다. page001의 실제101고유/21TASK를 확인해 TASK002–021로 돌아가도록 교정했고 page002 일부 초안은 보존했다. 모든 page의 TASK ID 집합·마지막TASK·담당고유수를 실제 manifest와 대조한 독립 인덱스를 새로 만들었다. 첫TASK/페이지 수를 전량 처리수로 세지 않는다.
- field의 실제 TASK/ROOT_IDENTITY 경로는 canonical BASE/page/reading_packets이며 agents 아래가 아니었다. 담당자가 agents prefix를 붙여 NoSuchFile이 반복됐다. 원문/후보 전문과 직접diff를 실제 읽은 대체 판독은 허용하되 실패한packet을 판독으로 세지 않는다. 정확 byte/pin 사본을 담당자 자기폴더에 새로 만들고 검산·읽기전용 허가를 제공했다. 기존 경로/원문은 변경하지 않았다.
- 포럼의 원래 오류 코드·의도적인 빈칸/미완 예제를 단순 구문오류만으로 추출손상으로 판단하지 않도록 보호 기준을 강화했다. 원문질문/답변에 의미가 있는 반례는 보존하고, 실제 추출소실 근거가 있는 단위만 분리한다. 이는 모든 과거body의 독립의미검토 완료 증거가 아니다.

다른유형50162의 실제native 준비0과98페이지읽기준비3단계0은 별도 receipt가 소유한다. aliases/위치명확화/정적구문증거는 전체 정제나 모델 품질·학습 재개를 증명하지 않는다. 전체 goal은 active다.
