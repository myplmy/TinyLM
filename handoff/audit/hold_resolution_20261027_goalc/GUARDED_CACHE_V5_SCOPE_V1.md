# 다음 캐시에 누적 보호 계약을 적용하는 범위

전체 정제 goal의 CPU 전처리·캐시 구현과 검증 승인을 적용한다. 이번 착수는 adapter와 metadata runtime preflight이며 아직 ROOT12 승인·새 캐시 생성은 아니다.

| 안 | 장점 | 비용·한계 |
|---|---|---|
| 기존 엔진에 새 V3 계약을 context adapter로 적용 | 검증한 EOS·경계·기존 예외·consumer 재사용 | runtime pin과 원복/alias 경계를 확인해야 함 |
| 새 cache engine 전체 fork | 독립 구현 가능 | 직렬화·검증을 다시 구현하고 유지해야 함 |
| 원장 delta overlay만 소비 | 전체 cache 재생성 비용 절감 | tokenizer/EOS/분할/중복 소비 계약이 새로 필요 |

첫 번째 안을 선택한다. 고정 V1–V4 파일과 기존 캐시는 보존하며, 실제 runtime 동안에만 CONTRACT를 V3로 연결한다. 기존 세 안전 view·코드/Unicode 보호·정확 pair 예외·검토된 HOLD 분리·독립 consumer는 그대로 유지한다. V3의 원문 8건/해시 9개/alias 13개를 사용하고 새 28876 두 위치 모두 원형 디코드 없이 처리한다.

코드 영향은 새 adapter와 preflight에 한정한다. 데이터 변경은 없다. 실제 metadata context에서 보호 목록·pin·원복을 검사하되 native 전체 scan/build/verify는 호출하지 않는다. positive alias와 unknown alias 거부는 별도 counter 입력 검산의 opaque fixture로 이미 확인했다. 이 preflight는 전체 새 cache PASS가 아니다.

원문·기존 캐시·TinyDataset·체크포인트·로그·타 세션·GPU/모델·외부 Git은 변경하지 않는다. intermediate WIP/감사만 갱신하며, 실제 ROOT/roster/cache가 생기기 전 정본의 채택 수량을 바꾸지 않는다.
