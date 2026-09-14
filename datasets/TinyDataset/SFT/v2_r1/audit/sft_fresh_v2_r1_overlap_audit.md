# SFT용 Fresh 코퍼스 v2 8-token 연속 일치 감사

- 상태: `OVERLAP_AUDIT_PASS`
- 단위: 지정 tokenizer의 연속 8-token window
- 보호 자산은 읽기 전용으로 검사했으며 모델·GPU는 사용하지 않음

| 비교 | query scope | query windows | protected windows | exact shared types | query occurrences | protected occurrences |
|---|---|---:|---:|---:|---:|---:|
| held-out v2.8 | full package natural-language fields | 18,246,072 | 1,244,639 | 0 | 0 | 0 |
| ko-en 600M train.bin | train messages only | 8,813,524 | 596,999,993 | 0 | 0 | 0 |

ko-en의 일치는 일반 표현까지 포함한 측정치이며 자동 폐기 기준이 아니다. held-out v2.8
일치는 0건을 통과 기준으로 삼는다. 전체 공유 유형은 JSONL에 한 유형당 한 줄로 기록했다.
