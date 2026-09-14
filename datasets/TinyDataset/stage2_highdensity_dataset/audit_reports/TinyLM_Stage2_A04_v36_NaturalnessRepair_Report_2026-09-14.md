# TinyLM Stage2 A04 v36 자연성 직접 수정·재감사 보고서

## 범위와 경계

- 대상: `sources/train/stage2_(14)state_transition_high_density_train_v36.source.jsonl` 한 파일의 150행.
- 수정: 모든 행을 직접 읽고, 붙여쓴 내부 상태명과 `primary은/는` 도입을 자연스러운 명사구와 상황 설명으로 개별 재서술했다.
- 보존: `relations`, 행 순서, 파일명, 레코드 수를 유지했다.
- 제외: A04의 다른 source, 다른 Stage2 영역, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기, GPU·학습·Git.

## 직접 검토·수정 결과

v36은 저장장치의 보조전원·통신·충방전·냉각·안전 격리·기록 복구 전이를 다룬다. `저온방전열경로수리`, `흡수상태`, `복구경로` 같은 내부식 표기를 `저장장치 방전용 저온 모듈 수리`, `저장장치 고온 충전 모듈 격리`처럼 실제 작업자가 읽을 수 있는 개념어로 바꿨다.

본문은 단순 정의 대신 관찰 조건, 판단·조치, 결과를 설명한다. 충전과 방전의 대칭 문장 12행은 각각의 실제 조건과 조치가 드러나도록 다시 썼고, 그 결과 5어절 반복과 같은 relations 집단의 고유사 쌍을 모두 해소했다. 전역 치환·번호 부여·전체 재직렬화는 하지 않았다.

## 수정 전후 해시

| 구분 | SHA-256 |
| --- | --- |
| 자연성 정리 착수 전 source | `77BA7EB34027666436311FF0B0BDC06D2A171AFEA995FA45BDF59FE74DD125F6` |
| 최종 source | `679320761F2DCC217D630C615033A84FE7D7D403A4538DAF19F39A2110E4E55E` |
| 최종 reviewer-assist 보고서 | `DCD68FEB9CEE831E413E29194D1BBE5758C2FA4063909475032AE4E559F0EF9B` |
| A04 정본 token 감사 스냅샷 | `5524363B8353A0052006A4DD7C6C2C10B01122F22B0485CAEE94CD2017542EAC` |

## 파일 단위 최종 재감사

| 항목 | 결과 |
| --- | ---: |
| records / UTF-8 BOM / 공백행 / JSON / schema | 150 / 없음 / 0 / 0 / 0 |
| 빈 primary·text / primary literal 누락 | 0 / 0 |
| 13개 통제 relations 위반 / cardinality 위반 / 내부 중복 | 0 / 0 / 0 |
| exact primary·text 중복 / 숫자 primary / 대시 primary | 0 / 0 / 0 |
| `primary+은/는` 도입 | 0 / 150 (0%) |
| 직접 5어절 반복 / 4어절 도입부 반복 | 0종·0회 / 0종·0회 |
| reviewer hard source error / 자연성 warning | 0 / 0 |
| reviewer 직접 수정·ChatGPT·사용자 queue | 0 / 0·0·0 |
| text 토큰(+EOS) / 평균 / 최소–최대 | 5,844 / 38.960000 / 30–46 |

토큰 계산은 `data_cache/tok-ko-en-32768.json`의 BPE와 EOS 1개를 사용했다. 평균 38.960000은 파일 평균 목표 범위 37.4625–45.7875 안이다.

독립 파일 한정 계산은 NFKC/lowercase 문자 3–5-gram TF-IDF와 word-set Jaccard를 같은 relations 집단의 574쌍에 전수 적용했다.

| 독립 유사도 | 임계치 초과 | 최고값 |
| --- | ---: | --- |
| 문자 3–5-gram TF-IDF cosine | 0 (`≥0.72`) | 0.520094061 (`고온 충전 감속` ↔ `고온 방전 감속`) |
| word-set Jaccard | 0 (`≥0.60`) | 0.545454545 (`고온 충전 감속` ↔ `고온 방전 감속`) |

## relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 67 |
| classification | 44 |
| boundary | 59 |
| contrast | 0 |
| comparison | 62 |
| function | 57 |
| role | 56 |
| process | 104 |
| state | 100 |
| attribute | 51 |
| other | 0 |

`other` 행이 없으므로 자주 나온 유형 5개는 해당 없다.

## 판정

- v36 구조·중복·유사도·조사·토큰·자연성: **PASS**
- A04 영역 전체 자연성·구조: **아직 HOLD** — 남은 HOLD 파일의 행별 재서술이 필요하다. 또한 전수 독립 구조 감사에서 기존 v33/v35 사이의 exact primary 2쌍(`저장장치 방전 계량 마감`, `저장장치 제한 운전 해제`)이 발견되어 다음 직접 수정 대상으로 유지한다. 이 보고서는 v36 한 파일만 대상으로 하며, 영역 완료·package·checkpoint 승격을 주장하지 않는다.

최종 기계 보고서: `machine/TinyLM_Stage2_A04_ReviewerAssist_v36_FinalAfterRepeat5Fix_2026-09-14.json`.
