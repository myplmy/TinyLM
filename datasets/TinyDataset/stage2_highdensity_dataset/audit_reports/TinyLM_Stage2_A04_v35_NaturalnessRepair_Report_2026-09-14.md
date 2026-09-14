# TinyLM Stage2 A04 v35 자연성 직접 수정·재감사 보고서

## 범위와 경계

- 대상: `sources/train/stage2_(14)state_transition_high_density_train_v35.source.jsonl` 한 파일의 150행만.
- 수정: 모든 행을 직접 읽고, 붙여쓴 전이명·정의형 문장·`primary은/는` 도입을 자연스러운 명사구와 상황 설명으로 개별 재서술했다.
- 보존: `relations`, 행 순서, 파일명, 레코드 수를 유지했다.
- 제외: A04의 다른 source, 다른 Stage2 영역, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기, GPU·학습·Git.

## 직접 검토·수정 결과

v35는 저장장치의 가역성, 되돌릴 수 없는 물리 변화, 운전·정산 기록 보존의 경계를 다룬다. `가역성경계`, `비가역성`처럼 붙여쓴 내부 표기는 `저장장치 충전 시작에서 남는 변화`, `저장장치 정비 허가 기록`, `저장장치 냉각수 누출`처럼 사람이 읽을 수 있는 개념어로 바꿨다.

본문은 단순한 정의가 아니라 무엇을 다시 바꿀 수 있고 무엇이 남는지를 설명하도록 썼다. 이후 직접 5어절 반복 24종·51회를 locator별로 다시 분리했고, 긴 설명도 뜻을 잃지 않는 범위에서 행별로 압축했다. 전역 치환·번호 부여·전체 재직렬화는 하지 않았다.

## 수정 전후 해시

| 구분 | SHA-256 |
| --- | --- |
| 자연성 정리 착수 전 source | `517FE770B8BCC009CFA86BBDF348076C336603A3C8E1191773B860E35E39007F` |
| 최종 source | `8F33EC12F7D6668EDC5DE7B46A62C8DDBEEFFC664C9E80443279E42A9535DE7D` |
| 최종 reviewer-assist 보고서 | `BF0BEC31F18055B296BB56D8C4656CD60814FCC9124F35ABE1BFACDDB850807E` |

## 파일 단위 최종 재감사

| 항목 | 결과 |
| --- | ---: |
| records / UTF-8 BOM / 공백행 / JSON / schema | 150 / 없음 / 0 / 0 / 0 |
| 빈 primary·text / primary literal 누락 | 0 / 0 |
| 13개 통제 relations 위반 / cardinality 위반 / 내부 중복 | 0 / 0 / 0 |
| exact primary·text 중복 / 숫자 primary / 대시 primary | 0 / 0 / 0 |
| `primary+은/는` 도입 | 0 / 150 (0%) |
| 직접 5어절 반복 / 4어절 도입부 반복 | 0종·0회 / 0종·0회 |
| 독립 문자 3–5-gram TF-IDF cosine ≥0.72 | 0 / 560 동일 relation-set pair |
| 독립 TF-IDF 최고 | 0.261751280 (`저장장치 상태 추정기 초기화` ↔ `저장장치 제어기 소프트 리셋`) |
| 독립 word-set Jaccard ≥0.60 | 0 / 560 동일 relation-set pair |
| 독립 Jaccard 최고 | 0.325000000 (`저장장치 상태 추정기 초기화` ↔ `저장장치 제어기 소프트 리셋`) |
| hard pattern / 인접 중복어 / primary 조사 후보 | 0 / 0 / 0 |
| reviewer 자연성 warning / 직접 수정·ChatGPT·사용자 queue | 0 / 0·0·0 |
| text 토큰(+EOS) / 평균 / 최소–최대 | 6,745 / 44.966667 / 35–51 |

토큰 계산은 `data_cache/tok-ko-en-32768.json`의 BPE와 EOS 1개를 사용했다. 평균 44.966667은 현재 파일 평균 목표 범위 37.4625–45.7875 안이다. 독립 유사도 계산은 reviewer-assist를 import하지 않은 파일 한정 계산으로, NFKC/lowercase 문자 3–5-gram TF-IDF와 word-set Jaccard를 동일 relation-set의 560쌍에 전수 적용했다.

## relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 28 |
| classification | 45 |
| boundary | 150 |
| contrast | 150 |
| comparison | 20 |
| function | 28 |
| role | 45 |
| process | 46 |
| state | 47 |
| attribute | 41 |
| other | 0 |

`other` 행이 없으므로 자주 나온 유형 5개는 해당 없다.

## 판정

- v35 구조·중복·유사도·조사·토큰·자연성: **PASS**
- A04 영역 전체 자연성: **아직 HOLD** — 이 보고서는 v35 한 파일만 대상으로 하며, 남은 HOLD 파일의 행별 재서술과 A04 전체 재감사가 끝나기 전에는 영역 완료·package·checkpoint 승격을 주장하지 않는다.

최종 기계 보고서: `machine/TinyLM_Stage2_A04_ReviewerAssist_v35_FinalAfterTokenAndRepeatFix_2026-09-14.json`.
