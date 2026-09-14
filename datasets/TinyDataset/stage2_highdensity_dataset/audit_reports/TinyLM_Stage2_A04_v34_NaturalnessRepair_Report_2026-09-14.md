# TinyLM Stage2 A04 v34 자연성 직접 수정·재감사 보고서

## 범위와 경계

- 대상: `sources/train/stage2_(14)state_transition_high_density_train_v34.source.jsonl` 한 파일의 150행만.
- 수정: 각 행을 직접 읽고, 사람이 읽을 수 있는 짧은 명사구 `primary`와 관찰·조건·조치·결과가 드러나는 `text`로 개별 재서술했다.
- 보존: `relations`, 행 순서, 파일명, 레코드 수를 유지했다.
- 제외: A04의 다른 source, A05·A06 등 다른 영역, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기, GPU·학습·Git.

## 직접 검토·수정 결과

v34의 150행은 붙여쓴 판단명과 `primary은/는`으로 시작하는 균일한 도입 문형을 모두 직접 검토했다. 예를 들어 `저장장치 보조 전원 투입 조건판정`류의 내부 작업 표기는 `저장장치 보조 전원 투입 기준`처럼 실제로 읽을 수 있는 개념어로, 본문은 단순 기록 지시가 아니라 전원 상태·안전 신호·운전 조치가 이해되도록 바꿨다.

직접 패치 뒤 남은 충전/방전 출력 관련 유사문장과 5어절 반복, 4어절 도입부 반복도 해당 locator만 다시 읽어 별도 상황 설명으로 재서술했다. 전역 치환·번호 부여·전체 재직렬화는 하지 않았고, 숫자 접미사·대시 qualifier·절단 어근·임의 합성어를 넣지 않았다.

## 수정 전후 해시

| 구분 | SHA-256 |
| --- | --- |
| 자연성 정리 착수 전 source | `67C3A5A2710E63A8829D37C1544EFF42DDAAADDA363CD2F082562A6B68237E93` |
| 최종 source | `9FE854EABA3BA6D2FDFFC61B3A8885284E77A61C5BBFDD796EC583BAA588F175` |
| 최종 reviewer-assist 보고서 | `6ACF4493F676B8D0514D25107D47408F331BBB3AEC0501483A5AF697E1296C3C` |

## 파일 단위 최종 재감사

| 항목 | 결과 |
| --- | ---: |
| records / UTF-8 BOM / 공백행 / JSON / schema | 150 / 없음 / 0 / 0 / 0 |
| 빈 primary·text / primary literal 누락 | 0 / 0 |
| 13개 통제 relations 위반 / cardinality 위반 / 내부 중복 | 0 / 0 / 0 |
| exact primary·text 중복 / 숫자 primary / 대시 primary | 0 / 0 / 0 |
| `primary+은/는` 도입 | 0 / 150 (0%) |
| 직접 5어절 반복 / 4어절 도입부 반복 | 0종·0회 / 0종·0회 |
| 독립 문자 3–5-gram TF-IDF cosine ≥0.72 | 0 / 712 동일 relation-set pair |
| 독립 TF-IDF 최고 | 0.451104075 (`저장장치 충전 완료 확정 조건` ↔ `저장장치 방전 완료 확정 조건`) |
| 독립 word-set Jaccard ≥0.60 | 0 / 712 동일 relation-set pair |
| 독립 Jaccard 최고 | 0.333333333 (`저장장치 충전 완료 확정 조건` ↔ `저장장치 방전 완료 확정 조건`) |
| hard pattern / 인접 중복어 / primary 조사 후보 | 0 / 0 / 0 |
| reviewer 자연성 warning / 직접 수정·ChatGPT·사용자 queue | 0 / 0·0·0 |
| text 토큰(+EOS) / 평균 / 최소–최대 | 6,505 / 43.366667 / 34–59 |

토큰 계산은 `data_cache/tok-ko-en-32768.json`의 BPE와 EOS 1개를 사용했다. 평균 43.366667은 현재 파일 평균 목표 범위 37.4625–45.7875 안이다. 독립 유사도 계산은 reviewer-assist를 import하지 않은 파일 한정 계산으로, NFKC/lowercase 문자 3–5-gram TF-IDF와 word-set Jaccard를 동일 relation-set의 712쌍에 전수 적용했다.

## relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 37 |
| classification | 52 |
| boundary | 150 |
| contrast | 0 |
| comparison | 62 |
| function | 42 |
| role | 38 |
| process | 150 |
| state | 32 |
| attribute | 37 |
| other | 0 |

`other` 행이 없으므로 자주 나온 유형 5개는 해당 없다.

## 판정

- v34 구조·중복·유사도·조사·토큰·자연성: **PASS**
- A04 영역 전체 자연성: **아직 HOLD** — 이 보고서는 v34 한 파일만 대상으로 하며, 남은 HOLD 파일의 행별 재서술과 A04 전체 재감사가 끝나기 전에는 영역 완료·package·checkpoint 승격을 주장하지 않는다.

최종 기계 보고서: `machine/TinyLM_Stage2_A04_ReviewerAssist_v34_Final_2026-09-14.json`.
