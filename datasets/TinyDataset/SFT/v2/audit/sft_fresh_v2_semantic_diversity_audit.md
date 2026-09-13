# SFT용 Fresh 코퍼스 v2 의미 다양성 감사

- 상태: `SEMANTIC_SOURCE_FAMILY_AUDIT_FAIL`
- 학습·평가 사용 승인: `false`
- 모델·GPU·학습·checkpoint·모델 평가: `NOT_RUN`

## 검사 방법

각 source의 `primary_concept`에서 접미사 `이름`을 제거해 가공어 어간을 얻고,
`source_text` 안의 같은 어간을 모두 `<가공어>`로 치환했다. 색·재질·위치·행동과 문장
구조는 그대로 보존했다. 이 검사는 source ID나 family 라벨만 바꾼 개념명 슬롯 교체를
찾기 위한 것이다.

## 결과

| 구분 | records | 정규화 고유 유형 | 중복 유형군 | 최대 반복 |
|---|---:|---:|---:|---:|
| v2 train | 22,200 | 5,553 | 2,865 | 641 |
| v2 eval | 360 | 273 | — | — |
| v1 train 비교 | 1,000 | 998 | 2 | 2 |
| v1 eval 비교 | 300 | 300 | 0 | 1 |

v2 eval의 정규화 유형 273개가 모두 train과 겹쳤고, eval 360건 전부가 그 공유 유형에
속했다. 따라서 라벨 기준 source-family 교집합 0은 실제 상황 계보의 분리를 증명하지 못한다.

## 판정

현재 산출물은 tokenizer·canonical·명시적 분포·보호 코퍼스 8-token 감사에는 통과했지만,
의미 수준의 train/eval 격리와 유효 다양성에서는 실패했다. 학습이나 평가에 사용하면 안 된다.

권장 조치는 현재 draft를 삭제하지 않고 보존한 뒤, 실제 topic·상황·문장 구조가 다양한 새
revision을 만들고 `stem-normalized train/eval 교집합 0`을 hard gate로 추가하는 것이다.
