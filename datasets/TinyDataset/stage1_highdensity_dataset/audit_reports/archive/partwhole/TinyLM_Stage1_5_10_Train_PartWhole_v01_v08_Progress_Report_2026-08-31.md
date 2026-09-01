# TinyLM Stage1 (5)~(10) train — Part–Whole v01~v08 누적 생성·감사 보고서

작성일: 2026-08-31  
정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`  
이전 checkpoint: `TinyLM_Stage1_5_10_Train_PartWhole_v01_v05_Progress_Report_2026-08-31.md`  
범위: 고밀도 train만 사용했으며 저밀도와 held-out은 source·schema·concept·중복/유사도 비교 기준에서 제외했다.

## 1. 결론과 진척

- 이전 확정 v01~v05를 보존하고 v06 `지층·암석·토양단면·유역·하천망`, v07 `은하·항성계·행성계·천체 내부`, v08 `건축 구조·외피·실내·설비`를 각각 150개씩 직접 작성했다.
- 실제 산출물은 `8 files × 150 = 1,200 records`, ID `S1-PWH-0001`~`S1-PWH-1200`이다. 150개 경계마다 예약 family와 파일을 정확히 전환했다.
- Stage1 (5)~(10) 전체 목표 `14,550 records = 97 files` 대비 `1,200/14,550 records`, `8/97 files`가 확정되었다. 잔여는 `13,350 records = 89 files`다.
- Stage1 (5)는 `1,200/3,450 records`, `8/23 files`이며 잔여는 `2,250 records = 15 files`다.
- 다음 재개점은 v09 `도로·교량·터널·상하수도 도시망의 구성`, ID `S1-PWH-1201`~`S1-PWH-1350`이다.

이 문서는 전체 97파일 생성 도중 v01~v08까지 실제로 확정된 범위를 보존하는 누적 checkpoint다.

## 2. 영역별 목표와 현재 상태

| 영역 | 목표 files | 목표 records | 현재 확정 | 잔여 |
|---|---:|---:|---:|---:|
| (5) 부분–전체 | 23 | 3,450 | 8 files / 1,200 | 15 files / 2,250 |
| (6) 상태·상태 변화 | 23 | 3,450 | 0 | 23 files / 3,450 |
| (7) 공간 관계 | 16 | 2,400 | 0 | 16 files / 2,400 |
| (8) 비교·대조 | 14 | 2,100 | 0 | 14 files / 2,100 |
| (9) 문맥 통합 | 12 | 1,800 | 0 | 12 files / 1,800 |
| (10) 타입·부정·불확실성 | 9 | 1,350 | 0 | 9 files / 1,350 |
| **합계** | **97** | **14,550** | **8 files / 1,200** | **89 files / 13,350** |

## 3. Part–Whole 확정 파일

| version | ID 범위 | concept family | JSON SHA-256 |
|---|---|---|---|
| v01 | 0001~0150 | 인체 기관계·기관·조직·세포의 구성 계층 | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| v02 | 0151~0300 | 식물 뿌리·줄기·잎·꽃·열매·종자의 구성 | `D3F104D88CE9E937678298304FA72D6C30DC2F14EFBF8EE58C3E2F5E9F1AD4D5` |
| v03 | 0301~0450 | 동물 골격·근육·외피·감각기관의 구성 | `B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0` |
| v04 | 0451~0600 | 세포 소기관·막계·분자복합체의 구성 | `4A300DA1D3A98908D3C7755A099B0441F7FF9587ACAEABBB5734DFEC8CD25763` |
| v05 | 0601~0750 | 생태계·먹이망·서식지·물질순환의 구성 | `81E61680850661343C0E3516804571CB5241F295F7E248CB96FEB348EF7A2975` |
| v06 | 0751~0900 | 지층·암석·토양단면·유역·하천망의 구성 | `6E0237695758F93DDB16DD4A3F37C684ACAFD0C9C322857293B6003FE04E3614` |
| v07 | 0901~1050 | 은하·항성계·행성계·천체 내부의 구성 | `0BA6A9608D6CA99D17F9B426D6371D82943755E21FE33CC665FC210D364E7485` |
| v08 | 1051~1200 | 건축 구조·외피·실내·설비의 구성 | `AA92D45F7613759751414F1B830C24D1BD37FE725CE5F723299B3BB44422867E` |

모든 파일은 top-level·record `split: train`, record `type: partwhole_packet`을 사용한다. 모든 record에는 primary concept가 text에 직접 나타나며 문장 수는 정확히 2개다. 누적 text는 102,788자, 정규식 분리 단위는 23,406개다. 길이는 최소 75자, 중앙값 85자, 평균 85.657자, 최대 110자다.

## 4. 직접 작성 범위와 자동화 경계

v06~v08의 concept와 text 450개를 source TSV에서 record별로 직접 작성했다. v06은 광물·암석·층서·토양층위·배수망, v07은 은하 구조·항성계·행성계·천체 내부·대기층, v08은 기초·골조·외피·실내 동선·전기·급배수·공조·소방·수직 운송을 서로 다른 객체 관계로 구성했다.

자동화는 source 검증, 연속 ID와 고정 schema 포장, JSON·중복·n-gram·도입부·유사도·조사 감사에만 사용했다. 같은 문장 틀의 명사 치환, 순차 문자열 치환, 저밀도 문장 복사, held-out 역참조는 사용하지 않았다. 증분 빌더는 앞선 확정 version의 source 재구성 기대 bytes를 확인하고 지정된 다음 version만 기록했다.

## 5. relations 통제 어휘 분포

모든 1,200 records는 `part_of`를 포함하고 각 record의 relations는 중복 없는 2~5개다. 통제 어휘 밖 relation은 0건이다.

| relation | v06 | v07 | v08 | v01~v08 누적 |
|---|---:|---:|---:|---:|
| `is_a` | 2 | 2 | 0 | 21 |
| `subclass_of` | 2 | 0 | 0 | 30 |
| `part_of` | 150 | 150 | 150 | 1,200 |
| `classification` | 97 | 73 | 41 | 499 |
| `boundary` | 35 | 25 | 30 | 240 |
| `contrast` | 26 | 25 | 9 | 144 |
| `comparison` | 7 | 13 | 2 | 38 |
| `function` | 16 | 15 | 132 | 524 |
| `role` | 0 | 6 | 3 | 106 |
| `process` | 38 | 28 | 43 | 242 |
| `state` | 14 | 42 | 15 | 150 |
| `attribute` | 25 | 9 | 8 | 150 |
| `other` | 35 | 60 | 17 | 241 |

v08의 `is_a`와 `subclass_of`가 0인 것은 실제 문장이 건축 조립체의 부분 관계와 기능을 설명하며 상하위 분류를 진술하지 않았기 때문이다. 분포를 채우기 위한 거짓 label은 추가하지 않았다.

## 6. `other` 상위 5개 개념 유형

아래 유형명은 source 감사용이며 JSON에는 모두 통제 relation `other`만 기록한다.

| 순위 | 편집 유형 | 누적 횟수 | 대표 의미 |
|---:|---|---:|---|
| 1 | aggregate identity / 집합 정체성 | 79 | 말뚝무리·성단·설비군처럼 독립 구성원을 전체로 묶는 경우 |
| 2 | abstract structure / 추상 구획·과정 구조 | 67 | 층서·궤도 구획·구조 그리드·실내 기능 영역처럼 물질 부품이 아닌 분할 |
| 3 | material portion / 물질적 몫 | 41 | 암석 조성·성간매질·천체 내부 물질처럼 재료량의 일부 |
| 4 | membership–component boundary / 구성원·구조부품 경계 | 28 | 천체계 구성원, 작업 좌석군과 공용 통로처럼 구성원과 내부 부품을 구별하는 경우 |
| 5 | provenance grouping / 공통 발생·생성 이력 묶음 | 26 | 퇴적·분화·형성 이력으로 여러 단위를 묶는 경우 |

## 7. v01~v08 누적 품질 감사

비교 대상은 현재 Stage1 (5)를 제외한 기존 고밀도 train·validation 21,700 records다. 저밀도와 held-out은 비교하지 않았다.

| 감사 항목 | 최종 결과 |
|---|---:|
| JSON parse / UTF-8 / Unicode escape 파일 | PASS / PASS / 0 |
| 파일 / records / ID 범위 | 8 / 1,200 / `S1-PWH-0001`~`1200` |
| schema / metadata / ID 오류 | 0 / 0 / 0 |
| source parse / source–JSON 불일치 | 0 / 0 |
| relation 규칙 오류 | 0 |
| duplicate ID / concept / exact text / concept–relation-set | 0 / 0 / 0 / 0 |
| 기존 고밀도와 exact concept / text / concept–relation-set | 0 / 0 / 0 |
| 내부 / 기존 고밀도 교차 반복 5어절 | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 오류 / 실제 광역 조사 오류 | 0 / 0 |
| control / unusual character 후보 | 0 / 0 |
| 내부 최대 문자 3~5-gram TF-IDF cosine | 0.340539 |
| 기존 고밀도 대비 최대 cosine | 0.322206 |

광역 조사 후보는 누적 16건이다. v08에서 늘어난 4건은 `맞닿는`, `주고받는`, `피난로`, `여닫는`의 어휘 말음을 조사로 오인한 false positive였고, 기존 후보를 포함해 실제 `은/는`, `이/가` 불량은 없었다. 내부 최대 유사 쌍은 이전부터 있던 일반 척주와 어류 척주 설명이며 객체 범위가 다른 정상 쌍이다.

v07 1차 감사에서 반복 5어절 5건과 75자 미만 12건을 찾아 원천 문장을 직접 다시 썼다. 비표준 개념명 `달내부와달진맨틀구성`도 `달내부와지진파감쇠맨틀구성`으로 교정했다. 수정 뒤 반복 구문은 0건, 최소 길이는 75자가 되었다. v08은 첫 누적 감사에서 모든 중복·반복 기준을 통과했다.

## 8. 신규 산출물 해시

| 산출물 | SHA-256 |
|---|---|
| `tools/stage1_relational_sources/partwhole/v06.tsv` | `8C114D96A4049184417BC97F69628EE42303AD17EE50BF26DB024F66BBB5B262` |
| `tools/stage1_relational_sources/partwhole/v07.tsv` | `77EA907BF5D4CD092BA36B331C6764EECF0AEB280583C60FDAB6EA8C886090A0` |
| `tools/stage1_relational_sources/partwhole/v08.tsv` | `2CC04BE774A1131B17C760CFA0778DE8F3BF3674D87838F2E68DAA431FCADA6D` |
| `TinyLM_Stage1_PartWhole_Train_v01_v06_Progress_Audit_2026-08-31.json` | `A1E31CB20E944F2BDE549014BDBCDC53AA05654AF5ABDBEA1FE8BA935714FC2C` |
| `TinyLM_Stage1_PartWhole_Train_v01_v07_Progress_Audit_2026-08-31.json` | `A2978107138BC691B5111C0A08BD62AF43BDC12BBA72EB7786AB1BFBA17C168E` |
| `TinyLM_Stage1_PartWhole_Train_v01_v08_Progress_Audit_2026-08-31.json` | `E914851CBE3A3DE5A631A0634D70FF8A18A6A40B7774CC30DF566FF3EAD01685` |

## 9. 정본 보호와 재개점

전체 생성 시작 때 고정한 Identity·Attribute·Function·Boundary와 Part–Whole v01 등 기존 정본 146개를 다시 계산한 결과 `146/146 SHA-256 일치`, 변경 0, 누락 0이었다. 증분 빌더는 이후 확정된 Part–Whole v02~v07도 source와 byte 일치를 검증한 뒤 v08만 썼다. Identity 계열은 수정하지 않았다.

```text
version: Stage1 (5) v09
ID: S1-PWH-1201 ~ S1-PWH-1350
family: 도로·교량·터널·상하수도 도시망의 구성
axes: 차로/도로, 교량 경간, 터널 단면, 관망, 맨홀·밸브·배수구
procedure: 150개 직접 작성 → v09만 기록 → v01~v09 누적 감사 → 통과 뒤 확정
```
