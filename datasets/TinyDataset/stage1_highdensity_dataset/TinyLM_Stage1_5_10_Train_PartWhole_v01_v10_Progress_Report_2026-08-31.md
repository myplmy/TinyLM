# TinyLM Stage1 (5)~(10) train — Part–Whole v01~v10 누적 생성·감사 보고서

작성일: 2026-08-31  
정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`  
직전 checkpoint: `TinyLM_Stage1_5_10_Train_PartWhole_v01_v08_Progress_Report_2026-08-31.md`  
범위: 고밀도 train만 사용. 저밀도와 held-out은 생성·참조·중복/유사도 비교에서 제외했다.

## 1. 확정 진척

- Part–Whole v01~v10 `10 files × 150 = 1,500 records`, ID `S1-PWH-0001`~`S1-PWH-1500`을 실제 생성·누적 감사했다.
- 이번 checkpoint 증분은 v09 `도로·교량·터널·상하수도 도시망의 구성`과 v10 `자동차·철도차량·자전거의 조립 계층`, 총 300개다.
- Stage1 (5)는 `1,500/3,450 records`, `10/23 files` 확정이며 잔여는 `1,950 records = 13 files`다.
- Stage1 (5)~(10) 전체는 `1,500/14,550 records`, `10/97 files` 확정이며 잔여는 `13,050 records = 87 files`다.
- 다음 재개점은 v11 `항공기·헬리콥터·우주선의 조립 계층`, ID `S1-PWH-1501`~`S1-PWH-1650`이다.

## 2. v09·v10 직접 작성 범위

v09는 도로 횡단면·교차로·포장·부대시설, 교량 상하부·경간·가동교, 도로·철도·공동구 터널, 취수·정수·상수 관망, 오수·우수·처리·침수 방재망으로 150개를 분산했다. v10은 자동차 차체·실내·동력계·전동화·조향·제동·현가, 철도차량 차체·대차·견인·제동·차상설비, 자전거 프레임·차륜·구동·제동·전동화로 150개를 분산했다.

모든 concept와 text는 source TSV에서 record별로 직접 작성했다. 자동화는 source 규칙 검증, ID·schema 포장과 감사에만 사용했다. 150개가 끝날 때 예약 family와 파일을 전환했으며 저밀도나 held-out 문장을 재사용하지 않았다.

## 3. 파일·분량·해시

| version | ID | family | JSON SHA-256 |
|---|---|---|---|
| v01 | 0001~0150 | 인체 기관계·기관·조직·세포 | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| v02 | 0151~0300 | 식물 기관·조직·생식구조 | `D3F104D88CE9E937678298304FA72D6C30DC2F14EFB8EE58C3E2F5E9F1AD4D5` |
| v03 | 0301~0450 | 동물 골격·근육·외피·감각기관 | `B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0` |
| v04 | 0451~0600 | 세포 소기관·막계·분자복합체 | `4A300DA1D3A98908D3C7755A099B0441F7FF9587ACAEABBB5734DFEC8CD25763` |
| v05 | 0601~0750 | 생태계·먹이망·서식지·물질순환 | `81E61680850661343C0E3516804571CB5241F295F7E248CB96FEB348EF7A2975` |
| v06 | 0751~0900 | 지층·암석·토양·유역·하천망 | `6E0237695758F93DDB16DD4A3F37C684ACAFD0C9C322857293B6003FE04E3614` |
| v07 | 0901~1050 | 은하·항성계·행성계·천체 내부 | `0BA6A9608D6CA99D17F9B426D6371D82943755E21FE33CC665FC210D364E7485` |
| v08 | 1051~1200 | 건축 구조·외피·실내·설비 | `AA92D45F7613759751414F1B830C24D1BD37FE725CE5F723299B3BB44422867E` |
| v09 | 1201~1350 | 도로·교량·터널·상하수도 도시망 | `872387810213933B90A83E9DDA921B015BC651E813B8CDE5917CE42839D8A539` |
| v10 | 1351~1500 | 자동차·철도차량·자전거 조립 계층 | `6D0C193216FF6E13940FAA9AAF6A85FA4903AB71DF75DA2B374C03AEC5FF9031` |

누적 text는 128,666자, 정규식 분리 단위는 29,232개다. record 길이는 최소 75자, 중앙값 86자, 평균 85.777자, 최대 110자이며 전 record가 정확히 두 문장이다.

## 4. relations 분포

모든 1,500 records는 `part_of`를 포함한다. record별 relations는 중복 없이 2~5개이며 통제 어휘 밖 label은 없다.

| relation | v09 | v10 | v01~v10 누적 |
|---|---:|---:|---:|
| `is_a` | 0 | 0 | 21 |
| `subclass_of` | 0 | 0 | 30 |
| `part_of` | 150 | 150 | 1,500 |
| `classification` | 46 | 31 | 576 |
| `boundary` | 34 | 20 | 294 |
| `contrast` | 7 | 7 | 158 |
| `comparison` | 1 | 1 | 40 |
| `function` | 123 | 139 | 786 |
| `role` | 0 | 1 | 107 |
| `process` | 41 | 45 | 328 |
| `state` | 22 | 35 | 207 |
| `attribute` | 4 | 3 | 157 |
| `other` | 22 | 18 | 281 |

v09·v10에서 `is_a`와 `subclass_of`가 0인 것은 각 문장이 시설·차량 조립체의 실제 부분, 기능, 상태와 경계를 설명하기 때문이다. 분포를 맞추기 위한 거짓 상하위 label은 넣지 않았다.

## 5. `other` 상위 5개 개념 유형

아래 유형은 source 감사용이며 JSON에는 모두 통제 relation `other`만 기록한다.

| 순위 | 유형 | 누적 |
|---:|---|---:|
| 1 | aggregate identity / 집합 정체성 | 100 |
| 2 | abstract structure / 추상 구획·과정 구조 | 80 |
| 3 | material portion / 물질적 몫 | 42 |
| 4 | membership–component boundary / 구성원·구조부품 경계 | 33 |
| 5 | provenance grouping / 공통 발생·생성 이력 묶음 | 26 |

대표 사례는 반복 경간·팬·센서·셀·스포크의 구성원 집합, 도로·관망 그래프와 기능 경로의 추상 구조, 합류 하수의 물질 몫, 계측기·정비품·공유 대차의 구성원/구조부품 경계다.

## 6. 누적 감사 결과

비교 범위는 현재 Part–Whole을 제외한 기존 고밀도 train·validation 21,700 records다.

| 감사 항목 | 결과 |
|---|---:|
| JSON / UTF-8 / schema / metadata / ID / source 대응 오류 | 0 |
| 통제 relation·개수·record 내 중복 오류 | 0 |
| duplicate ID / concept / exact text / concept–relation-set | 0 / 0 / 0 / 0 |
| 기존 고밀도 exact concept / text / concept–relation-set | 0 / 0 / 0 |
| 내부 / 기존 고밀도 교차 반복 5어절 | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 / 실제 광역 조사 오류 | 0 / 0 |
| control / unusual character 후보 | 0 / 0 |
| 내부 최대 문자 3~5-gram TF-IDF cosine | 0.340702 |
| 기존 고밀도 대비 최대 cosine | 0.322681 |

광역 조사 후보 20건은 `맞닿는`, `가까이`, `붙잡는`, `물통로`, `주고받는`, `피난로`, `여닫는`, `시트스테이` 등의 어휘 말음을 규칙 검사가 조사로 오인한 false positive다. 실제 조사 불량은 없었다.

v09 1차 감사에서 기존 고밀도와 반복된 일반 문구 1건과 75자 미만 1건을 직접 재작성했다. 터널 공법명도 `NATM` 표기로 교정했다. v10은 75자 미만 2건을 보강하고 `관절대차열차`를 `관절형열차`로 다듬었다. 최종 감사에서 반복·중복·길이 오류는 모두 0건이다.

## 7. 정본 보호·산출물·재개점

전체 작업 시작 때 고정한 기존 Identity·Attribute·Function·Boundary 및 Part–Whole v01 등 146개 정본은 `146/146 SHA-256 일치`, 변경 0, 누락 0이다. Identity 계열은 수정하지 않았다. 증분 빌더는 앞선 Part–Whole JSON을 source 재구성 결과와 byte 대조한 뒤 대상 version만 기록했다.

| 신규 산출물 | SHA-256 |
|---|---|
| `tools/stage1_relational_sources/partwhole/v09.tsv` | `62CB6C89DC339F132CA266DC7633CDEDF228F71FEE4979D2676C09E9EC2AB9C8` |
| `tools/stage1_relational_sources/partwhole/v10.tsv` | `B35E6ECA5A71D8AED6B0A7BFF29F6C26FD406B52C81B4DB82186F4B24F8BBBF3` |
| `TinyLM_Stage1_PartWhole_Train_v01_v09_Progress_Audit_2026-08-31.json` | `3C34F6E3D88D1AE73432DA71B581F1881909ED7D5130153517D6F5B5EE6FBA41` |
| `TinyLM_Stage1_PartWhole_Train_v01_v10_Progress_Audit_2026-08-31.json` | `1A89B2B2910EA1CC45924BDC965C01267E8AFEA141EE0E930E13A01067C9A900` |

```text
next version: Stage1 (5) v11
ID: S1-PWH-1501 ~ S1-PWH-1650
family: 항공기·헬리콥터·우주선의 조립 계층
axes: 동체/날개, 회전익, 추진·조종면, 항공전자, 탑재체·단계
procedure: source 150개 직접 작성 → v11만 기록 → v01~v11 누적 감사 → 통과 뒤 확정
```
