# TinyLM Stage1 (4) 개념 경계·반례 train v01~v31 최종 감사 보고서

- 감사 기준일: 2026-08-31 KST
- 상태: v01~v31 확정·수정 금지
- 범위: 고밀도 작업지침서·설계서 및 고밀도 Stage1 train/validation 정본
- 기계 판독 감사: `TinyLM_Stage1_Boundary_Train_v01_v31_Full_Audit_2026-08-31.json`
- 직접 작성 원문: `tools/boundary_sources/v01.tsv`~`v31.tsv`
- 패키징/감사: `tools/build_boundary_train.py`, `tools/audit_boundary_corpus.py`

## 1. 결론

Stage1 (4) 개념 경계·반례 train은 31개 concept family, 31개 JSON, 파일당 150개, 총 4,650개로 확정했다. ID는 `S1-BNH-0001`~`S1-BNH-4650`으로 연속하며 모든 record는 `type: boundary_packet`, `split: train`, 2~5개의 중복 없는 통제 relation을 갖는다. `boundary`는 4,650개 전 record에 존재한다.

JSON·UTF-8·schema·metadata·ID·source↔JSON·통제 relation 오류, exact ID/concept/text/concept–relation-set 중복, 내부 및 기존 고밀도 교차 5어절 반복, 4어절 도입부 반복, primary concept 조사 오류가 모두 0건이다. 기존 고밀도 정본과 exact concept·text·concept–relation-set 교집합도 모두 0건이다.

설계상의 약 378K는 tokenizer가 정해지기 전 record 기반 환산 목표다. 확정 corpus의 실측치는 `text` 423,235자, 정규식 분리 단위 103,517개이며 실제 model token 수로 오인하지 않는다.

## 2. 중단 전·재개 후 작업 연속성

PC 중단 뒤 파일명만으로 완료 지점을 추정하지 않고 원문 TSV 행 수, 생성 JSON, ID 범위와 기존 감사 결과를 대조했다. 중단 전에 완성된 v01~v23과 v24의 선작성 75개를 보존했고, v24 잔여 75개 및 v25~v31을 이어 작성했다. 따라서 중단 구간을 다시 생성해 concept·ID가 겹치거나 누락된 record는 없다.

재개 후 전체 4,650개를 다시 패키징했다. 직접 재작성 중 concept literal 불변조건을 만족하지 않은 원문은 빌더가 JSON 갱신 전에 차단했으며, 검사를 약화하지 않고 모든 concept 표기를 복원한 뒤 재실행했다.

1차 통합 감사에서 다음 실제 오류를 원문에서 고쳤다.

- `젤状` → `젤 형태`
- `마찰으로` → `마찰로`
- `법규과` → `법규와`, `법규이` → `법규가`
- `평줄과유선형샤더`, `우들투들`, `긎어` → `평줄과유선형샌더`, `우둘투둘`, `긁어`
- `레인코트와방수덮개은` → `레인코트와방수덮개는`

내부 반복 5어절 55건은 39개 문장군을 의미 보존 재작성해 0건으로 만들었다. 최고 유사 쌍이던 `매개와교란`과 `역인과와피드백`은 표면 치환하지 않고 각각 `매개경로와효과수정`, `피드백순환과일방향경로`로 비교 축을 새로 설계했다. 이어 기존 고밀도 정본과 공유하던 5어절 15건도 Boundary 원문 쪽만 재작성해 0건으로 만들었다.

## 3. 버전별 누적 확정표

| 버전 | 파일 | ID 범위 | records | 누적 | concept family | SHA-256 |
|---|---|---|---:|---:|---|---|
| v01 | `stage1_(4)boundary_high_density_train_v01.json` | `S1-BNH-0001~S1-BNH-0150` | 150 | 150 | 동물 분류·형태·행동의 경계 | `71ddcf1206761d8452d1c308edba5c29bc753764f4e881f56f2c24e0dbf883ab` |
| v02 | `stage1_(4)boundary_high_density_train_v02.json` | `S1-BNH-0151~S1-BNH-0300` | 150 | 300 | 식물·균류·조류·미생물 분류 경계 | `da8d52c55010a7b31226fb66239d2dd68458568e0c88d3835d2b7dcca202cca7` |
| v03 | `stage1_(4)boundary_high_density_train_v03.json` | `S1-BNH-0301~S1-BNH-0450` | 150 | 450 | 생태계·서식지·행동·관계의 경계 | `abbd2b9cef48c1e5b1ecf27e60b9fd806191b45f37adeeb14b399f2aee7d180b` |
| v04 | `stage1_(4)boundary_high_density_train_v04.json` | `S1-BNH-0451~S1-BNH-0600` | 150 | 600 | 인체 해부·생리·생체 신호 경계 | `b6067165e80e6a36e09cbf5d8625c01a09185d538afc0f805f810cd05806e996` |
| v05 | `stage1_(4)boundary_high_density_train_v05.json` | `S1-BNH-0601~S1-BNH-0750` | 150 | 750 | 증상·질환·검사·치료·예방 경계 | `2dfd8f9628afe005fa488e3207258353939e5d519b62d6d59e27b70e92fea892` |
| v06 | `stage1_(4)boundary_high_density_train_v06.json` | `S1-BNH-0751~S1-BNH-0900` | 150 | 900 | 식재료·음식·조리·발효·보존 경계 | `675e621c0470b389b5ffcd40b721e423224420eb77d7922b2e5fcd604a8383f7` |
| v07 | `stage1_(4)boundary_high_density_train_v07.json` | `S1-BNH-0901~S1-BNH-1050` | 150 | 1,050 | 재료·물질·혼합물·제품·제조 경계 | `d676a090a19e2aa65ad489061497b385293d29062db21b4b1772bc29948bf823` |
| v08 | `stage1_(4)boundary_high_density_train_v08.json` | `S1-BNH-1051~S1-BNH-1200` | 150 | 1,200 | 물리량·측정·힘·에너지·파동 경계 | `9ba1a8a6a5d8a826452619dbe0c6fcdb8a5e3cc83f49f8502ff4a15cb92f31fe` |
| v09 | `stage1_(4)boundary_high_density_train_v09.json` | `S1-BNH-1201~S1-BNH-1350` | 150 | 1,350 | 화학종·결합·용액·반응 경계 | `52233e4d5325481046e3f0474ecf5bccb2516239b1d0e999da7eb7d305499e79` |
| v10 | `stage1_(4)boundary_high_density_train_v10.json` | `S1-BNH-1351~S1-BNH-1500` | 150 | 1,500 | 지질·기상·수문·해양 현상 경계 | `cf2daee39c31d8683759d914c8b7f733f5cdf96ced52d61898fa79337a8497c9` |
| v11 | `stage1_(4)boundary_high_density_train_v11.json` | `S1-BNH-1501~S1-BNH-1650` | 150 | 1,650 | 천문·우주·관측 개념 경계 | `5b15ad9c7261dee61e4d7f30e239e8f19f078c218e0cee7b77c58597502ec85b` |
| v12 | `stage1_(4)boundary_high_density_train_v12.json` | `S1-BNH-1651~S1-BNH-1800` | 150 | 1,800 | 수·연산·대수·함수 개념 경계 | `c490d4c282c3000d94244e5ac980b4ac401e18c35ed1c7a5321bf02d5ebfa8c8` |
| v13 | `stage1_(4)boundary_high_density_train_v13.json` | `S1-BNH-1801~S1-BNH-1950` | 150 | 1,950 | 도형·공간·측정·기하 경계 | `b3194b29a52167e430d18272110a8e06df25d0688461d9da719d73d03957f240` |
| v14 | `stage1_(4)boundary_high_density_train_v14.json` | `S1-BNH-1951~S1-BNH-2100` | 150 | 2,100 | 확률·통계·표본·데이터 해석 경계 | `61b2838f91b3f5e9f44a23ea79a40b003f945135a7a0d09bb57f64a369248ffd` |
| v15 | `stage1_(4)boundary_high_density_train_v15.json` | `S1-BNH-2101~S1-BNH-2250` | 150 | 2,250 | 논리·집합·조건·인과·추론 오류 경계 | `fb12c8e7405660331c1ea726d8547168e6384ac5c0d8faca1d467dbc6434f7fe` |
| v16 | `stage1_(4)boundary_high_density_train_v16.json` | `S1-BNH-2251~S1-BNH-2400` | 150 | 2,400 | 언어·문법·의미·화용 경계 | `c3d86e54e1fa2a047e79073e6011f8401fd4dc4a7f563dc30d24c81c37fa5bb7` |
| v17 | `stage1_(4)boundary_high_density_train_v17.json` | `S1-BNH-2401~S1-BNH-2550` | 150 | 2,550 | 문서·정보·미디어·장르 경계 | `50def66edadd65b277358b59c6d5315fd8b84e9ade58cd10dcf441530449bc61` |
| v18 | `stage1_(4)boundary_high_density_train_v18.json` | `S1-BNH-2551~S1-BNH-2700` | 150 | 2,700 | 컴퓨팅·소프트웨어·데이터·네트워크 경계 | `846ba9ef552add8414eeeaf76949b64e3c73d13b09f807cfdaf2167d655bf3e8` |
| v19 | `stage1_(4)boundary_high_density_train_v19.json` | `S1-BNH-2701~S1-BNH-2850` | 150 | 2,850 | 전기·전자·기계·제어 시스템 경계 | `2bb1bbfbc612d07461c08a046baae14f11cd3530709beda5a94072af75366218` |
| v20 | `stage1_(4)boundary_high_density_train_v20.json` | `S1-BNH-2851~S1-BNH-3000` | 150 | 3,000 | 건축·건설·도시 기반시설 경계 | `b73649b7a026a6df55516d99ab8268befda3658791be514441a34fe3e9f6063b` |
| v21 | `stage1_(4)boundary_high_density_train_v21.json` | `S1-BNH-3001~S1-BNH-3150` | 150 | 3,150 | 생활도구·가전·의복·개인용품 경계 | `6e15a77d460846f4edb00ea1728797de8e91f8d1b2abb300ea733a5e74c3acae` |
| v22 | `stage1_(4)boundary_high_density_train_v22.json` | `S1-BNH-3151~S1-BNH-3300` | 150 | 3,300 | 교통·이동·항법·물류 경계 | `1ccac908bc8446a6caa2c9ed60e6c625aafdb16bedb6741aec039bdf198a939c` |
| v23 | `stage1_(4)boundary_high_density_train_v23.json` | `S1-BNH-3301~S1-BNH-3450` | 150 | 3,450 | 예술·음악·공연·시각디자인 경계 | `fc86bfb83fd99fa0f08e0bfde087cb891452265431c90ee5ab45cbb02aecd4f7` |
| v24 | `stage1_(4)boundary_high_density_train_v24.json` | `S1-BNH-3451~S1-BNH-3600` | 150 | 3,600 | 스포츠·게임·경기 규칙 경계 | `119d1421703c17c0731fcafe8644c4e7f6fdf0925b085d34d05df48f567db0da` |
| v25 | `stage1_(4)boundary_high_density_train_v25.json` | `S1-BNH-3601~S1-BNH-3750` | 150 | 3,750 | 교육·학습·평가·연구·출판 경계 | `24261e35f3fcb3b1509228242b049a2ec0ef616755bbc0b0d408b6982d3cc05c` |
| v26 | `stage1_(4)boundary_high_density_train_v26.json` | `S1-BNH-3751~S1-BNH-3900` | 150 | 3,900 | 법률·권리·의무·절차·증거 경계 | `a4ef623bc3c57ff0efe57ac256ba1673dbaa8d88128cea042febab6aaf51e70b` |
| v27 | `stage1_(4)boundary_high_density_train_v27.json` | `S1-BNH-3901~S1-BNH-4050` | 150 | 4,050 | 정부·정책·행정·공공서비스 경계 | `cfd81bf1246e6596fb2ab9ef44294330a854dc41273252352b196c177607b56e` |
| v28 | `stage1_(4)boundary_high_density_train_v28.json` | `S1-BNH-4051~S1-BNH-4200` | 150 | 4,200 | 경제·회계·금융·상거래 경계 | `035b3eb9a089d785e649fe55a13085a43180cd97d06ca5d02128f335fae6e675` |
| v29 | `stage1_(4)boundary_high_density_train_v29.json` | `S1-BNH-4201~S1-BNH-4350` | 150 | 4,350 | 사회관계·가족·조직·문화 경계 | `c638a73666244b65c9c8932dd6bc985e4547be49e552a0e438845e7e4bd1dbc7` |
| v30 | `stage1_(4)boundary_high_density_train_v30.json` | `S1-BNH-4351~S1-BNH-4500` | 150 | 4,500 | 지리·영토·환경·기후·에너지 경계 | `54fbf1adb27724bca9b59fe00e1b52b605087be4ecd578e805fef9bda05aea37` |
| v31 | `stage1_(4)boundary_high_density_train_v31.json` | `S1-BNH-4501~S1-BNH-4650` | 150 | 4,650 | 시간·상태·정체성·부정·불확실성 경계 | `8d30cc10de179059b260383142029a35a98e3e092a0dd6e350a7e7e432caf343` |

목표 4,650개, 현재 누적 4,650개, 잔여 0개/0파일이다. 31개 concept family 이름은 모두 고유하며 version 간 재사용이 없다.

## 4. Relations 통제 어휘 감사

허용된 13개 이름 밖의 relation은 0건이며, 각 record는 2~5개이고 record 내부 중복 이름은 0건이다.

| relation | 전체 횟수 | relation | 전체 횟수 |
|---|---:|---|---:|
| `is_a` | 7 | `subclass_of` | 90 |
| `part_of` | 382 | `classification` | 1,622 |
| `boundary` | 4,650 | `contrast` | 187 |
| `comparison` | 435 | `function` | 881 |
| `role` | 264 | `process` | 1,262 |
| `state` | 1,897 | `attribute` | 962 |
| `other` | 1,311 |  |  |

### 버전별 13개 relation 분포

| 버전 | is_a | subclass_of | part_of | classification | boundary | contrast | comparison | function | role | process | state | attribute | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v01 | 2 | 0 | 18 | 112 | 150 | 65 | 1 | 13 | 9 | 18 | 26 | 36 | 0 |
| v02 | 1 | 6 | 32 | 73 | 150 | 18 | 8 | 32 | 6 | 39 | 41 | 28 | 16 |
| v03 | 0 | 1 | 15 | 34 | 150 | 4 | 13 | 47 | 22 | 42 | 70 | 26 | 26 |
| v04 | 0 | 1 | 44 | 41 | 150 | 1 | 16 | 49 | 0 | 29 | 49 | 48 | 22 |
| v05 | 0 | 0 | 2 | 32 | 150 | 2 | 18 | 31 | 1 | 60 | 82 | 32 | 40 |
| v06 | 0 | 0 | 17 | 45 | 150 | 2 | 14 | 22 | 3 | 59 | 68 | 42 | 28 |
| v07 | 0 | 7 | 19 | 72 | 150 | 6 | 18 | 13 | 7 | 43 | 43 | 53 | 19 |
| v08 | 0 | 2 | 8 | 34 | 150 | 8 | 35 | 14 | 0 | 38 | 50 | 82 | 29 |
| v09 | 0 | 3 | 9 | 48 | 150 | 2 | 30 | 14 | 13 | 38 | 58 | 63 | 22 |
| v10 | 0 | 3 | 13 | 72 | 150 | 2 | 19 | 5 | 3 | 55 | 60 | 34 | 34 |
| v11 | 1 | 4 | 12 | 57 | 150 | 1 | 13 | 12 | 2 | 26 | 71 | 33 | 68 |
| v12 | 0 | 11 | 11 | 65 | 150 | 4 | 19 | 24 | 8 | 31 | 53 | 33 | 41 |
| v13 | 0 | 12 | 13 | 75 | 150 | 8 | 28 | 5 | 4 | 8 | 50 | 54 | 43 |
| v14 | 0 | 2 | 6 | 31 | 150 | 1 | 24 | 10 | 7 | 28 | 74 | 62 | 55 |
| v15 | 0 | 1 | 10 | 36 | 150 | 3 | 4 | 15 | 11 | 57 | 80 | 7 | 76 |
| v16 | 0 | 2 | 10 | 81 | 150 | 1 | 2 | 18 | 34 | 20 | 72 | 11 | 49 |
| v17 | 0 | 2 | 11 | 48 | 150 | 0 | 1 | 21 | 4 | 35 | 94 | 14 | 70 |
| v18 | 0 | 5 | 11 | 43 | 150 | 1 | 4 | 38 | 4 | 46 | 85 | 14 | 49 |
| v19 | 2 | 2 | 7 | 27 | 150 | 4 | 25 | 54 | 4 | 48 | 59 | 33 | 35 |
| v20 | 1 | 6 | 13 | 44 | 150 | 5 | 8 | 77 | 5 | 46 | 38 | 17 | 40 |
| v21 | 0 | 2 | 10 | 65 | 150 | 2 | 4 | 106 | 0 | 26 | 40 | 10 | 35 |
| v22 | 0 | 6 | 9 | 47 | 150 | 3 | 11 | 44 | 14 | 39 | 50 | 20 | 57 |
| v23 | 0 | 9 | 11 | 54 | 150 | 4 | 11 | 36 | 12 | 51 | 22 | 24 | 66 |
| v24 | 0 | 3 | 6 | 63 | 150 | 3 | 27 | 19 | 12 | 50 | 51 | 19 | 47 |
| v25 | 0 | 0 | 11 | 53 | 150 | 4 | 9 | 49 | 9 | 52 | 41 | 20 | 52 |
| v26 | 0 | 0 | 2 | 45 | 150 | 5 | 1 | 26 | 21 | 44 | 79 | 3 | 74 |
| v27 | 0 | 0 | 11 | 45 | 150 | 3 | 6 | 38 | 15 | 58 | 57 | 12 | 55 |
| v28 | 0 | 0 | 9 | 50 | 150 | 10 | 20 | 13 | 7 | 42 | 63 | 57 | 29 |
| v29 | 0 | 0 | 9 | 34 | 150 | 5 | 10 | 14 | 26 | 53 | 90 | 10 | 49 |
| v30 | 0 | 0 | 20 | 69 | 150 | 5 | 22 | 19 | 0 | 38 | 62 | 27 | 38 |
| v31 | 0 | 0 | 3 | 27 | 150 | 5 | 14 | 3 | 1 | 43 | 119 | 38 | 47 |

### `other` 상위 5개 편집 유형

`other`는 억지로 다른 label을 붙이지 않고 통제 어휘의 의미 경계를 지키기 위해 사용했다.

| 순위 | 편집 유형 | 횟수 | 자주 나온 개념 유형 | 대표 concept |
|---:|---|---:|---|---|
| 1 | 증거·추론 범위 | 461 | 검출 실패와 부재, 관측과 원인, 지표와 확정 판단 | `검출불가와부재` |
| 2 | 표현–지시대상 간극 | 356 | 명칭과 실제 대상, 지도·모형과 현실, 표상과 물리 구조 | `먹이사슬과실제먹이망` |
| 3 | 규범·권한 범위 | 314 | 권고와 의무, 허가와 권리, 기관의 법정 권한 | `권고와법적의무` |
| 4 | 문맥·관례 의존 | 137 | 일상 분류와 학술 분류, 관용 명칭, 맥락별 의미 | `과일과열매` |
| 5 | 필요·충분 논리 | 43 | 한 증상과 진단, 한 기능과 기관, 가능성과 확정 | `한증상과한진단` |

## 5. 형식·중복·문장 품질 감사

| 감사 항목 | 결과 |
|---|---:|
| JSON/UTF-8 parse 오류 | 0 |
| 파일 수/record 수 | 31/4,650 |
| 파일별 150개 위반 | 0 |
| ID 범위·연속성 오류 | 0 |
| schema 오류 | 0 |
| top-level metadata 오류 | 0 |
| source TSV parse 오류 | 0 |
| source↔JSON 불일치 | 0 |
| 통제 relation 오류 | 0 |
| exact ID 중복 | 0 |
| exact primary concept 중복 | 0 |
| exact text 중복 | 0 |
| exact concept–relation-set 중복 | 0 |
| 내부 반복 5어절 | 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 조사 오류 | 0 |
| control character | 0 |
| Unicode escape 포함 파일 | 0 |

광범위 조사 탐지기는 79개 record를 후보로 냈다. 79개 전체 원문을 사람이 다시 읽은 결과 `가까이`, `주고받는`, `전문가`, `플레이`, `릴레이` 같은 어간·부사·명사를 조사 결합으로 오인한 false positive였으며 추가 실제 오류는 없었다. 이 수치는 오류 79건을 뜻하지 않는다.

특수문자 후보 17건은 `₂`, `⁺`, `÷`, `±`, `²`, `³`, `≠`, `¬`, `∨`로, 화학식·수학·논리 표기에 필요한 정상 문자임을 record별로 확인했다. 한자 혼입이나 비정상 제어문자는 없다.

문장 길이는 최소 51자, 중앙값 80자, 평균 91.018자, 최대 176자다. 1문장 record는 196개, 2문장 record는 4,454개다. 형식적으로 두 문장을 강제하지 않고 개념 경계와 반례 또는 판정 기준이 충분히 담겼는지를 우선했다.

## 6. 유사도·고밀도 분리 감사

문자 3~5-gram TF-IDF cosine을 전체 고밀도 corpus 기준으로 계산했다.

- Boundary 내부 최대: `0.353981`
- 기존 고밀도 Stage1 train/validation과 최대: `0.382725`
- 내부 exact concept/text/concept–relation-set 중복: 모두 0
- 기존 고밀도와 exact concept/text/concept–relation-set 교집합: 모두 0
- 내부 반복 5어절: 0
- 기존 고밀도와 공유 5어절: 0

내부 상위 쌍은 `규제표지와안내표지`↔`도로규제표지와방향안내표지` 0.353981, `비율과퍼센트포인트`↔`백분율과퍼센트포인트` 0.348792, `조건긍정과결과긍정`↔`결과부정과조건부정` 0.336671이다. 모두 같은 family 안에서 서로 다른 혼동 경계를 의도적으로 분리한 record이며 문장과 relation-set은 다르다.

고밀도 교차 상위 쌍은 Boundary `반지름과지름`과 Identity `지름`의 0.382725다. Identity가 대상 정의를, Boundary가 반지름과 지름의 혼동 기준을 가르치므로 교육 목적이 다르고 exact 문장·객체–relation 조합도 겹치지 않는다. 그 밖의 상위 쌍도 정의 대상과 경계 판정 과제가 분리된 정상적인 인접 개념 쌍으로 확인했다.

## 7. 문서 분리와 정본성 확인

`TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`에는 재사용 가능한 작업 순서, 직접 작성 원칙, JSON·ID·relation·validation 분리·감사·보고 규칙만 남겼다. 특정 데이터셋의 완료 이력, token/record 배분, concept family 원장, ID 범위, 실측 relation 분포, 감사 결과와 수정 금지 목록은 `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`로 이관했다.

설계서에는 기존 Identity·Attribute·Function 정본 상태와 Stage1 (4)의 31개 family, 생성·재개·수정·감사 결과를 갱신했다. 다음 작업자는 작업지침서와 설계서를 함께 읽으면 과거 continuity 문서 없이도 보호 범위, 형식, 분리 규칙, 감사·보고 요구를 복원할 수 있다.

## 8. 보호 파일 무결성

작업 시작 전에 Identity·Attribute·Function train/validation 및 존재하는 보호 pattern 파일 110개의 SHA-256을 고정했다. 종료 시 같은 대상 110개를 다시 계산한 결과 `110/110 동일`, 추가·누락 0개였다. 특히 `stage1_(1)identity_high_density_*` 계열은 읽기·해시 비교 외에 수정하지 않았다.

이번 생성과 교차 감사는 고밀도 작업지침서·설계서와 고밀도 Stage1 train/validation만 기준으로 수행했다. 다른 밀도의 corpus는 문장 source, 참고 기준, schema 근거, 중복 비교 대상으로 사용하지 않았다.

## 9. 최종 판정

v01~v31은 요청한 31개 고유 concept family와 150개 단위를 모두 충족한다. 4,650개 전 record가 형식·relation·중복·반복·조사·고밀도 분리 감사를 통과했으므로 Stage1 (4) 개념 경계·반례 train 정본으로 확정한다. 이후 변경은 새 사용자 승인과 변경 전·후 전체 재감사를 전제로 한다.
