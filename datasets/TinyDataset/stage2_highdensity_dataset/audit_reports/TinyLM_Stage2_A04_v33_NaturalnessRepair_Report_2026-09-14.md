# TinyLM Stage2 A04 v33 자연성 직접 수정·재감사 보고서

## 범위와 경계

- 대상: `sources/train/stage2_(14)state_transition_high_density_train_v33.source.jsonl` 한 파일 150행만.
- 수정: 모든 행을 직접 읽고, 자연스러운 짧은 명사구 `primary`와 관찰·조건·조치·결과가 읽히는 `text`로 개별 재서술했다. `relations`, 행 순서, 파일명은 유지했다.
- 제외: A04의 다른 source, A05·A06 등 다른 영역, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기, GPU·학습·Git.

## 직접 검토·수정 결과

기존의 붙여쓴 전이명과 `primary은/는` 도입 문형 150건을 개별 검토했다. `냉각출력상향 전이`, `접촉기개방 실패전이`, `열한계 재계산전이`처럼 사람에게 바로 읽히지 않는 표현은 `냉각 출력 높이기`, `접촉기 개방 실패`, `온도 제한 재계산`처럼 상황에 맞는 짧은 명사구로 바꿨다.

본문은 제목을 그대로 정의하는 문장이 아니라, 무엇을 확인하고 어떤 조건에서 장치를 조치하며 결과가 어떻게 달라지는지 설명하도록 다시 썼다. 예를 들어 온도 감시·냉각·가열·보호 잠금·정비 모드·폐기 전 분리를 각각 다른 관찰 조건과 조치로 설명했다. 숫자 접미사, 대시 qualifier, 절단 어근, 임의 합성어는 넣지 않았다.

파일 단위 독립 계산에서 남은 5어절 반복 1개(`계통과 배터리의 안전 조건을 다시`, 충전/방전 재개 2행)를 확인했다. 전역 치환하지 않고 충전 재개 행을 전압·온도·계통 허가 확인이라는 별도 설명으로 다시 썼고, 최종 반복은 0이 됐다.

## 수정 전후 해시

| 구분 | SHA-256 |
| --- | --- |
| 자연성 정리 착수 전 source | `4A4CE678C143096479E8204B84FE3063671768676CA4E9F804CEEBD065B982F2` |
| 최종 source | `E20D33E1A6DCCA97AEF884A6E66D062310E76B4A74B37530165715DF8E096379` |
| 최종 reviewer-assist 보고서 | `62B10E671695B1184A7CCDD5F96511EDBF67DBCF76C4B0ABB99EB50B45D857EF` |

첫 번째 최종 후보 보고서는 마지막 5어절 교정 전 스냅샷이므로 최종 판정에 사용하지 않았다. 아래의 `FinalAfterRepeat5Fix` 보고서가 정본이다.

## 파일 단위 최종 재감사

| 항목 | 결과 |
| --- | ---: |
| records / UTF-8 BOM / 공백행 / JSON / schema | 150 / 없음 / 0 / 0 / 0 |
| 빈 primary·text / primary literal 누락 | 0 / 0 |
| 13개 통제 relations 위반 / cardinality 위반 / 내부 중복 | 0 / 0 / 0 |
| exact primary·text 중복 / 숫자 primary / 대시 primary | 0 / 0 / 0 |
| `primary+은/는` 도입 | 0 / 150 (0%) |
| 직접 5어절 반복 / 4어절 도입부 반복 | 0종·0회 / 0종·0회 |
| 독립 문자 3–5-gram TF-IDF cosine ≥0.72 | 0 / 761 동일 relation-set pair |
| 독립 TF-IDF 최고 | 0.439092726 (`충전 일시 정지` ↔ `방전 일시 정지`) |
| 독립 word-set Jaccard ≥0.60 | 0 / 761 동일 relation-set pair |
| 독립 Jaccard 최고 | 0.357142857 (`충전 계획 변경` ↔ `방전 계획 변경`) |
| hard pattern / 인접 중복어 / primary 조사 후보 | 0 / 0 / 0 |
| reviewer 자연성 warning / 직접 수정·ChatGPT·사용자 queue | 0 / 0·0·0 |
| text 토큰(+EOS) / 평균 / 최소–최대 | 5,857 / 39.046667 / 30–51 |

평균 39.046667은 현재 파일 평균 목표 범위 37.4625–45.7875 안이다. 독립 유사도 계산은 reviewer-assist를 import하지 않은 파일 한정 계산으로, NFKC/lowercase 문자 3–5-gram TF-IDF와 word-set Jaccard를 동일 relation-set의 761쌍에 전수 적용했다.

## relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 30 |
| classification | 16 |
| boundary | 44 |
| contrast | 0 |
| comparison | 44 |
| function | 61 |
| role | 40 |
| process | 150 |
| state | 150 |
| attribute | 65 |
| other | 0 |

`other` 행이 없으므로 자주 나온 유형 5개는 해당 없다.

## 판정

- v33 구조·중복·유사도·조사·토큰·자연성: **PASS**
- A04 영역 전체 자연성: **아직 HOLD** — 이 보고서는 v33 한 파일만 대상으로 하며, 남은 HOLD 파일의 행별 재서술과 A04 전체 재감사가 끝나기 전에는 영역 완료·package·checkpoint 승격을 주장하지 않는다.

최종 기계 보고서: `machine/TinyLM_Stage2_A04_ReviewerAssist_v33_FinalAfterRepeat5Fix_2026-09-14.json`.
