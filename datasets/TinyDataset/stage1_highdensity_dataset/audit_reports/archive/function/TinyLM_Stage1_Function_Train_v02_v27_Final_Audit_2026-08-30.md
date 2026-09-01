# TinyLM Stage 1 Function Train v02~v27 생성·최종 감사 보고서

- 기준일: 2026-08-30 KST
- 대상: `stage1_(3)function_high_density_train_v02.json`~`v27.json`
- 신규 생성: 26개 파일, 3,900 records
- 누적 감사: v01~v27, 27개 파일, 4,050 records
- 누적 ID: `S1-FNH-0001`~`S1-FNH-4050`
- 판정: **PASS — v01~v27 확정 및 수정 금지 전환 가능**

## 1. 중단 전·후 연속성과 작업 범위

PC 오류 뒤 재개할 때 실제 파일과 작성 소스, 예약 concept-family 원장, Function v01 SHA-256, 보호 대상 파일의 SHA-256 기준선을 먼저 확인했다. 이미 작성된 v02~v25 소스와 산출물은 중복 생성하지 않고 이어서 사용했으며, 누락된 v26·v27을 직접 작성한 뒤 v02~v27 전체를 동일 builder로 다시 생성했다. 마지막에는 v01을 포함한 4,050 records를 한 번에 재감사했다.

의미 `text`, primary concept, relations 선택은 record별 직접 작성 literal이다. 자동화는 TSV literal을 ID·metadata가 있는 JSON으로 포장하고 구조·중복·유사도를 감사하는 데만 사용했다. `stage1_(1)identity_*`, `stage1_(2)attribute_*`, 기존 Function v01은 수정하지 않았다.

## 2. 파일·개념군·누적·SHA-256

| 버전 | 파일 | ID 범위 | concept family | records | 누적 | SHA-256 |
|---|---|---|---|---:|---:|---|
| v01 | `stage1_(3)function_high_density_train_v01.json` | `S1-FNH-0001`~`S1-FNH-0150` | 수동 작업·정비·제작 공구의 기능 | 150 | 150 | `02b8974c56b7733b57c94f742c88a4bb170fc55c5ede83f76038e673620cb2e7` |
| v02 | `stage1_(3)function_high_density_train_v02.json` | `S1-FNH-0151`~`S1-FNH-0300` | 식재료 준비·조리·제공 기구의 기능 | 150 | 300 | `dd0e15cf8bd6c35aa2bd161565bdabfe0b41aabbe90da074d9c0694ad6e68703` |
| v03 | `stage1_(3)function_high_density_train_v03.json` | `S1-FNH-0301`~`S1-FNH-0450` | 식품 보존·포장·위생·품질 관리 장치의 기능 | 150 | 450 | `f19718f8eee10c9f32aa37dcaed940ecbe7c25a593447f8cd58220c5c320d44c` |
| v04 | `stage1_(3)function_high_density_train_v04.json` | `S1-FNH-0451`~`S1-FNH-0600` | 의복·신발·착용 보호·휴대 구성품의 기능 | 150 | 600 | `28522aeb5f3f07208d2ca45d4bbfa5e7684a3e81e9d50bf3276c8ae0781cf9a7` |
| v05 | `stage1_(3)function_high_density_train_v05.json` | `S1-FNH-0601`~`S1-FNH-0750` | 청소·세탁·건조·생활 폐기물 처리 도구의 기능 | 150 | 750 | `2e21f246bfa1fe9fd8329321ec692c15a1eca3c41a65e019c384ee4c22bf1e5f` |
| v06 | `stage1_(3)function_high_density_train_v06.json` | `S1-FNH-0751`~`S1-FNH-0900` | 건물 외피·개구부·실내 마감·공간 조절 구성품의 기능 | 150 | 900 | `60f2a4cb8cc7acb263ad22fe9e636603687ed0059fcc6b7dc03fe8af4d289118` |
| v07 | `stage1_(3)function_high_density_train_v07.json` | `S1-FNH-0901`~`S1-FNH-1050` | 급배수·위생·환기·냉난방 실내 설비의 기능 | 150 | 1,050 | `b69dacf887f6b7b1ff0e18a3d83037112ee874e39ec27a01f80699c17780a35f` |
| v08 | `stage1_(3)function_high_density_train_v08.json` | `S1-FNH-1051`~`S1-FNH-1200` | 농림·축산·수산 생산 도구와 설비의 기능 | 150 | 1,200 | `9744fb4d9096ebd51c5a5a624fcf207996e460b46b6a002899231a855b6e8156` |
| v09 | `stage1_(3)function_high_density_train_v09.json` | `S1-FNH-1201`~`S1-FNH-1350` | 육상·항공·해상 교통수단과 부품의 기능 | 150 | 1,350 | `bb9795c9a30e594e12c1886f47714903f8c7064ec172ce4ffcdd89454044585f` |
| v10 | `stage1_(3)function_high_density_train_v10.json` | `S1-FNH-1351`~`S1-FNH-1500` | 포장·하역·운반·분류·보관 물류 장비의 기능 | 150 | 1,500 | `a2e44c067de76edbd9e143aa0e8847a63ba188a50882cc4afb22004e9da3e473` |
| v11 | `stage1_(3)function_high_density_train_v11.json` | `S1-FNH-1501`~`S1-FNH-1650` | 제조 성형·절삭·접합·조립 생산 설비의 기능 | 150 | 1,650 | `23d985acc77b7c1fa2dc29f357cba4f08f8c8713e1bec43f2c2448290e6cf026` |
| v12 | `stage1_(3)function_high_density_train_v12.json` | `S1-FNH-1651`~`S1-FNH-1800` | 품질검사·공정제어·설비진단·유지보수 장치의 기능 | 150 | 1,800 | `598ba37474a50afc7647cb29c210cd4fdd3fb52322c930830790212c979f9a02` |
| v13 | `stage1_(3)function_high_density_train_v13.json` | `S1-FNH-1801`~`S1-FNH-1950` | 도로·교량·철도·터널·배수 공공 인프라의 기능 | 150 | 1,950 | `426a20bfc4bc0227275719a9c5fb4689234fbde458cdcceb4cd65fc811e8c6cc` |
| v14 | `stage1_(3)function_high_density_train_v14.json` | `S1-FNH-1951`~`S1-FNH-2100` | 물 공급·하수처리·위생·자원회수 도시 서비스의 기능 | 150 | 2,100 | `d054db1c71c5c9164cf8b76143c3b77b7abd4d497f44a92da9c107de7e3059c4` |
| v15 | `stage1_(3)function_high_density_train_v15.json` | `S1-FNH-2101`~`S1-FNH-2250` | 에너지 생산·변환·저장·송배전·보호 장치의 기능 | 150 | 2,250 | `40635af2c41ccfe701e55267eb90221c016bdefd59312cd95b00d3aefbb435a0` |
| v16 | `stage1_(3)function_high_density_train_v16.json` | `S1-FNH-2251`~`S1-FNH-2400` | 전자회로·센서·신호처리·구동 부품의 기능 | 150 | 2,400 | `01818c6214491dfbd1290962267b5019c4f22f861b4c508fb1f22499558fe4f1` |
| v17 | `stage1_(3)function_high_density_train_v17.json` | `S1-FNH-2401`~`S1-FNH-2550` | 컴퓨팅 처리·기억·저장·입출력 장치의 기능 | 150 | 2,550 | `16d5af1dd0b9d7f31bc60bba58e8845fd61253f6644a0d6bb37e3a9d02e27517` |
| v18 | `stage1_(3)function_high_density_train_v18.json` | `S1-FNH-2551`~`S1-FNH-2700` | 네트워크·소프트웨어·데이터 서비스의 기능 | 150 | 2,700 | `2cc52c2df63f83f28d60413fedf444d922404e38057a0899abd173cde0ce4cd5` |
| v19 | `stage1_(3)function_high_density_train_v19.json` | `S1-FNH-2701`~`S1-FNH-2850` | 통신·미디어 기록·편집·전송·표현 도구의 기능 | 150 | 2,850 | `9526a09332adc4d4440caa6f6dfa8d492e39ab8fc2d6aceb83eea99baaf800e8` |
| v20 | `stage1_(3)function_high_density_train_v20.json` | `S1-FNH-2851`~`S1-FNH-3000` | 실험실 채취·분리·반응·계량·교정 장비의 기능 | 150 | 3,000 | `0e11893cdfdb3a0a2346d412bcf2bb588efb0651afcd963962f8eeee23fb74a9` |
| v21 | `stage1_(3)function_high_density_train_v21.json` | `S1-FNH-3001`~`S1-FNH-3150` | 의료 진단·치료·모니터링·재활·감염관리 기구의 기능 | 150 | 3,150 | `360e6a878d0bd849c3fb0d6ff82e9d258ad65c54c9d28322584521880f12e9b1` |
| v22 | `stage1_(3)function_high_density_train_v22.json` | `S1-FNH-3151`~`S1-FNH-3300` | 생물 기관·세포 구조·생태계 구성원의 기능 | 150 | 3,300 | `41e4b6ff9a5ad5ef9079d04895af5ef07b104d4e0d755262f4f37673687758e0` |
| v23 | `stage1_(3)function_high_density_train_v23.json` | `S1-FNH-3301`~`S1-FNH-3450` | 환경 감시·오염 정화·자원 순환·생태 복원 시설의 기능 | 150 | 3,450 | `bf04348aa8a4b723cf5859ab968a7f5f01b892bb6c9149571160cd1100eec920` |
| v24 | `stage1_(3)function_high_density_train_v24.json` | `S1-FNH-3451`~`S1-FNH-3600` | 안전·재난·보안·구조·접근성 보조 장치의 기능 | 150 | 3,600 | `15384da6ea232de36abfa6b32c92a6012a888478842c336147383f686def86bb` |
| v25 | `stage1_(3)function_high_density_train_v25.json` | `S1-FNH-3601`~`S1-FNH-3750` | 교육·학습·도서관·문서화 도구의 기능 | 150 | 3,750 | `9702d9694370b56fb6b6315613a45eca28608638e222aec94a371dcd9a90a8b7` |
| v26 | `stage1_(3)function_high_density_train_v26.json` | `S1-FNH-3751`~`S1-FNH-3900` | 상업·금융·거래·고객 서비스 체계의 기능 | 150 | 3,900 | `0b0ed07ddda27deccc617bc1ca2603989b1e7e2f432c65baf141f7486792bd25` |
| v27 | `stage1_(3)function_high_density_train_v27.json` | `S1-FNH-3901`~`S1-FNH-4050` | 공공행정·법률·복지·지역사회·문화 서비스의 기능 | 150 | 4,050 | `5dde8188d4c0bac65ff1be5c5352c5f5d4ab717bce68f0797aa8acf8ccd347dd` |

약 324K tokens는 4,050-record 설계 환산량이므로 packet 기준 목표를 충족했다. 현재 정본 학습 tokenizer가 지정되어 있지 않아 모델 token 수로 단정하지 않는다. 참고 실측은 `text` 합계 253,352자, `[0-9A-Za-z가-힣]+` 기준 공백·문장부호 분리 단위 61,667개다.

## 3. 구조·형식 감사

| 항목 | 결과 |
|---|---:|
| 파일 수 / record 수 | 27 / 4,050 |
| 파일별 record 수 | 전부 150 |
| JSON parse·UTF-8 실패 | 0 |
| 한국어 `\uXXXX` escape 파일 | 0 |
| top-level metadata 오류 | 0 |
| record schema 오류 | 0 |
| ID 불연속·범위 오류 | 0 |
| duplicate ID | 0 |
| duplicate primary concept | 0 |
| duplicate exact text | 0 |
| 통제 어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relations 2~5개 위반 | 0 |
| `function` 누락 | 0 |

relations 수는 2개인 record 3,322개, 3개인 record 728개이며 4~5개를 억지로 채운 record는 없다. 모든 record의 `type`은 `function_packet`, `split`은 `train`이고 Function train에는 `unseen_relation`을 넣지 않았다.

본문 길이는 최소 35자, 중앙값 55자, 평균 62.556자, 최대 166자다. 문장 수는 1문장 4,021개, 2문장 29개다.

## 4. Relations 통제 어휘 분포

### 4.1 전체 v01~v27

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| `is_a` | 2 | `subclass_of` | 42 |
| `part_of` | 340 | `classification` | 187 |
| `boundary` | 526 | `contrast` | 10 |
| `comparison` | 224 | `function` | 4,050 |
| `role` | 1,036 | `process` | 1,144 |
| `state` | 779 | `attribute` | 488 |
| `other` | 0 |  |  |

`other`는 0건이다. 따라서 `other`로 분류한 것 중 자주 나온 개념 유형 5가지는 **해당 없음**이다. 이번 corpus는 모든 관계가 나머지 12개 명명 관계로 정직하게 표현되어 0이 된 것이며, 0을 목표로 relation을 왜곡한 것은 아니다.

### 4.2 버전별 13개 분포

| 버전 | is_a | subclass_of | part_of | classification | boundary | contrast | comparison | function | role | process | state | attribute | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v01 | 1 | 5 | 2 | 6 | 17 | 10 | 7 | 150 | 50 | 45 | 3 | 79 | 0 |
| v02 | 0 | 2 | 8 | 2 | 22 | 0 | 9 | 150 | 29 | 27 | 15 | 46 | 0 |
| v03 | 1 | 2 | 6 | 3 | 28 | 0 | 6 | 150 | 30 | 39 | 21 | 23 | 0 |
| v04 | 0 | 2 | 50 | 4 | 19 | 0 | 6 | 150 | 53 | 6 | 29 | 33 | 0 |
| v05 | 0 | 4 | 22 | 6 | 27 | 0 | 7 | 150 | 27 | 36 | 17 | 30 | 0 |
| v06 | 0 | 3 | 47 | 3 | 18 | 0 | 7 | 150 | 56 | 16 | 23 | 27 | 0 |
| v07 | 0 | 6 | 28 | 6 | 18 | 0 | 9 | 150 | 40 | 26 | 43 | 8 | 0 |
| v08 | 0 | 2 | 11 | 6 | 19 | 0 | 3 | 150 | 40 | 43 | 22 | 17 | 0 |
| v09 | 0 | 3 | 69 | 3 | 11 | 0 | 4 | 150 | 50 | 28 | 43 | 11 | 0 |
| v10 | 0 | 5 | 12 | 7 | 15 | 0 | 6 | 150 | 45 | 17 | 34 | 26 | 0 |
| v11 | 0 | 5 | 16 | 5 | 19 | 0 | 7 | 150 | 29 | 52 | 27 | 11 | 0 |
| v12 | 0 | 0 | 5 | 1 | 21 | 0 | 11 | 150 | 46 | 38 | 23 | 10 | 0 |
| v13 | 0 | 0 | 28 | 1 | 15 | 0 | 6 | 150 | 67 | 22 | 27 | 12 | 0 |
| v14 | 0 | 2 | 5 | 6 | 16 | 0 | 6 | 150 | 30 | 47 | 29 | 17 | 0 |
| v15 | 0 | 0 | 4 | 3 | 11 | 0 | 7 | 150 | 33 | 46 | 41 | 9 | 0 |
| v16 | 0 | 1 | 3 | 5 | 20 | 0 | 9 | 150 | 17 | 47 | 27 | 25 | 0 |
| v17 | 0 | 0 | 0 | 8 | 9 | 0 | 4 | 150 | 39 | 53 | 37 | 0 | 0 |
| v18 | 0 | 0 | 0 | 5 | 29 | 0 | 4 | 150 | 39 | 38 | 30 | 5 | 0 |
| v19 | 0 | 0 | 0 | 0 | 19 | 0 | 0 | 150 | 45 | 53 | 29 | 4 | 0 |
| v20 | 0 | 0 | 0 | 2 | 11 | 0 | 8 | 150 | 18 | 71 | 27 | 13 | 0 |
| v21 | 0 | 0 | 5 | 6 | 14 | 0 | 6 | 150 | 27 | 48 | 30 | 14 | 0 |
| v22 | 0 | 0 | 3 | 5 | 8 | 0 | 0 | 150 | 48 | 61 | 22 | 3 | 0 |
| v23 | 0 | 0 | 0 | 10 | 14 | 0 | 0 | 150 | 6 | 93 | 13 | 14 | 0 |
| v24 | 0 | 0 | 1 | 11 | 24 | 0 | 1 | 150 | 36 | 33 | 39 | 5 | 0 |
| v25 | 0 | 0 | 1 | 29 | 10 | 0 | 5 | 150 | 33 | 42 | 30 | 0 | 0 |
| v26 | 0 | 0 | 9 | 21 | 43 | 0 | 48 | 150 | 40 | 63 | 45 | 31 | 0 |
| v27 | 0 | 0 | 5 | 23 | 49 | 0 | 38 | 150 | 63 | 54 | 53 | 15 | 0 |

분포는 기능 corpus의 실제 문장 의미를 따랐다. 모든 버전에 relation 13종을 인위적으로 한 번씩 배치하지 않았고, 기능·역할·과정·상태가 자연스럽게 많은 구조를 유지했다.

## 5. 중복·보일러플레이트·유사도 감사

| 항목 | 결과 |
|---|---:|
| exact text 중복 | 0 |
| exact primary concept 중복 | 0 |
| 내부 반복 5어절 문구 | 0 |
| 반복 4어절 도입부 | 0 |
| 내부 문자 3~5-gram TF-IDF 최고 cosine | 0.357568 |
| 저밀도 prototype 교차 최고 cosine | 0.211338 |

내부 고유사도 상위쌍은 `마이크로폰캡슐–전화송화기` 0.357568, `밀링머신–셰이퍼` 0.357046, `전기집진필터–집진전극` 0.353173, `총유기탄소분석기–연소식총유기탄소분석기` 0.351205, `실린더카트–가스실린더랙` 0.349963이다. 각 문장을 직접 대조한 결과, 복제 문장이 아니라 입력·작동 원리나 상위 기능을 공유하면서 대상·조건·역할이 다른 가까운 개념쌍이다. 최고값도 0.36 미만이므로 매우 유사한 문장 반복으로 판정할 항목은 없다.

`concept + 은/는`으로 시작하는 설명형 문체는 schema 목적에 맞는 자연스러운 공통 형식이지만, 그 뒤 기능 서술은 record별로 다르다. exact 5어절 반복과 4어절 도입부 반복이 모두 0이므로 고정 문구를 채워 넣은 보일러플레이트는 검출되지 않았다.

## 6. 조사·문장 품질·수동 재독

primary concept 직후 `은/는`, `이/가` 선택을 포함한 직접 조사 오류 검출은 0건이다. 넓은 휴리스틱이 낸 후보 30건은 전부 문맥 재검토했다. `가까이`, `달라붙는`, `가라앉는` 같은 부사·관형형, `트레이`, `스프레이`, `게이트웨이` 같은 외래어, `취득가`, `잔존가`, `전문가`처럼 조사와 같은 음절로 끝나는 명사였으며 실제 조사 오류는 없었다.

작성 중 batch별 재독과 전체 손상 패턴 검색을 병행했다. 최종 교정에는 잘못 끊긴 조사·활용, 오탈자, 깨진 음절, 부정확한 전문어, 의미가 뒤집힌 표현, 불필요하게 모호한 문장을 포함했다. 특히 v19~v27은 최종 단계에서 전수 재독했고, v02~v27 전체에 알려진 손상 패턴을 다시 검색했다. 마지막 검색에 남은 `흠집`, `예초기`, `흰지팡이` 등은 모두 정상어였다.

## 7. 저밀도 Function prototype 분리

기존 `stage1_dataset`의 `S1-FUNC-*` prototype 120개와 비교한 결과:

- exact primary concept 교집합: 0
- exact text 교집합: 0
- 5어절 이상 문구 교집합: 0
- 교차 최고 문자 3~5-gram TF-IDF cosine: 0.211338

따라서 고밀도 Function train은 기존 저밀도 prototype 문장을 복사하지 않았고, primary concept도 정확히 겹치지 않는다.

## 8. 수정 금지 파일과 범위 무결성

작업 시작 때 저장한 보호 대상 81개와 종료 시 SHA-256을 비교했다.

- identity train v01~v41: 41/41 일치
- identity validation v01~v04: 4/4 일치
- attribute train v01~v31: 31/31 일치
- attribute validation v01~v04: 4/4 일치
- Function train v01: 1/1 일치
- 합계: **81/81 일치, 변경 0**

Function v01 SHA-256은 시작과 종료 모두 `02b8974c56b7733b57c94f742c88a4bb170fc55c5ede83f76038e673620cb2e7`이다. 현재 workspace에는 `stage2_(2)attribute_high_density_*` 일치 파일이 없었으며, 지침서의 이름 패턴 보호 규칙은 유지했다. 작업 범위 밖에서 관찰된 `../../test_result/` log와 최종 Git 상태의 `../../scripts/check_hf_redirect.py`, `../../scripts/diag_chat_overhead.py`, `../../scripts/diag_dataset_tokens.py`, `../../handoff/WIP_20260830d_작업원장.md` 변경은 편집·정리·stage하지 않고 그대로 보존했다.

## 9. 정본 산출물과 재현 명령

정본 감사 JSON:

```text
TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json
```

직접 작성 소스와 포장·감사 도구:

```text
tools/function_sources/v02.tsv ... v27.tsv
tools/build_function_train_v02_v27.py
tools/audit_function_corpus.py
```

repository root에서 실행:

```powershell
$env:PYTHONIOENCODING='utf-8'
python stage1_highdensity_dataset\tools\build_function_train_v02_v27.py .
python stage1_highdensity_dataset\tools\audit_function_corpus.py . --similarity-limit 500 --output stage1_highdensity_dataset\TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json
```

최종 결론: v02~v27의 3,900 records와 기존 v01을 합친 Function train 4,050 records는 지정한 27개 concept family, 연속 ID, 직접 작성 원칙, 13개 relation 통제 어휘, 형식·중복·유사도·조사·prototype 분리 기준을 통과했다. Function train v01~v27 전체를 확정·수정 금지 상태로 전환한다.
