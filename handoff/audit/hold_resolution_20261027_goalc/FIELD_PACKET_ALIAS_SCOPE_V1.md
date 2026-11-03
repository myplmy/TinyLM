# 담당자별 읽기 전용 packet 사본

실제 TASK/manifest의 packet 부모는 BASE/remaining_field_title_page_NNN_counter_v1다. 원문 경로가 정확한데도 agents/역할 prefix를 추가한 호출이 반복해 실패했다. 실패를 읽기 완료로 보지 않으며, 실제 native 전문+직접diff의 대체 판독은 그대로 허용된 범위다.

| 안 | 영향/비용 | 판단 |
|---|---|---|
| 원래 경로만 반복 안내 | 추가 I/O없음, 같은 경로 혼동이 반복됨 | 기존 안내 유지 |
| 모든 역할에 새Python 도구를 추가 | 경로추측 감소,읽기 예외/CLI 회귀 부담 | 미적용 |
| 네 raw읽기 역할의 자기 폴더에 정확 바이트 사본 제공 | 수십MB 추가 로컬I/O,같은 packet 읽기 모델 | 적용 |

새 사본은 역할에 이미 배정된 exact packet만 포함한다. ID/SHA 보호 경계를 먼저 확인하고 원본 pin/새 사본 SHA·bytes를 모두 대조한다. 한 파일20MB미만이며 원본/기존후보/기존캐시/도구/registry는 변경하지 않는다. controls는 이 raw사본 대상에서 제외하고 기존 고정reader를 유지한다.

코드 영향은 새copy/index뿐이며 실제 prose 정제는0이다. 새readonly 사본과 source는 동일한 한 문서여서 새고유자료/새독립판독으로 세지 않는다. root는 새자기 page 하위reading_packets_v1만 만들며 Luna 출력/오류초안/리뷰를 건드리지 않는다. 스키마·훈련·모델 비교에는 영향이 없다. 원문/사본 exact pin의 실제 대조가 검사다. 이후 WIP/소형감사근거에 연결하고 대량사본은 Git에 넣지 않는다. GPU·모델·학습·외부다운로드·타세션·TinyDataset·push/PR은 제외다.
