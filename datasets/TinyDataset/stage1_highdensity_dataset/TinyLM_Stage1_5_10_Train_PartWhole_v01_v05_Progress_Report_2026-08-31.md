# TinyLM Stage1 (5)~(10) train — Part–Whole v01~v05 누적 생성·감사 보고서

작성일: 2026-08-31  
정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`  
이전 checkpoint: `TinyLM_Stage1_5_10_Train_PartWhole_v01_v03_Progress_Report_2026-08-31.md`  
범위: 고밀도 train만 사용. 저밀도와 held-out은 source·schema·concept·중복/유사도 비교 기준에서 제외했다.

## 1. 결론과 진척

- 이전 확정본 Stage1 (5) v01~v03 450 records를 byte 단위로 보호하고, 이번 continuation에서 v04와 v05를 각각 150개씩 직접 작성했다.
- 신규 family는 v04 `세포 소기관·막계·분자복합체의 구성`, v05 `생태계·먹이망·서식지·물질순환의 구성`이다. 150개가 끝날 때 family와 파일을 정확히 전환했다.
- 현재 실제 산출물은 Part–Whole v01~v05, `750 records = 5 files × 150`, ID `S1-PWH-0001`~`S1-PWH-0750`이다.
- Stage1 (5)~(10) 전체 목표 `14,550 records = 97 files` 대비 현재 진척은 `750/14,550 records`, `5/97 files`다. 잔여는 `13,800 records = 92 files`다.
- Stage1 (5)는 `750/3,450 records`, `5/23 files`가 확정되었고 잔여는 `2,700 records = 18 files`다.
- Stage1 (6)~(10)은 아직 실제 JSON을 만들지 않았으며 설계서 §16~§20의 예약 순서를 유지한다.
- 다음 재개점은 Stage1 (5) v06 `지층·암석·토양단면·유역·하천망의 구성`, ID `S1-PWH-0751`~`0900`이다.

전체 97파일 목표는 계속 진행 중이다. 이 문서는 v01~v05까지 실제로 확정된 범위를 증명하는 누적 checkpoint다.

## 2. 영역별 전체 목표와 현재 상태

| 영역 | 목표 files | 목표 records | 현재 확정 | 잔여 |
|---|---:|---:|---:|---:|
| (5) 부분–전체 | 23 | 3,450 | 5 files / 750 | 18 files / 2,700 |
| (6) 상태·상태 변화 | 23 | 3,450 | 0 | 23 files / 3,450 |
| (7) 공간 관계 | 16 | 2,400 | 0 | 16 files / 2,400 |
| (8) 비교·대조 | 14 | 2,100 | 0 | 14 files / 2,100 |
| (9) 문맥 통합 | 12 | 1,800 | 0 | 12 files / 1,800 |
| (10) 타입·부정·불확실성 | 9 | 1,350 | 0 | 9 files / 1,350 |
| **합계** | **97** | **14,550** | **5 files / 750** | **92 files / 13,800** |

## 3. Part–Whole 확정 파일

| version | ID 범위 | concept family | JSON SHA-256 |
|---|---|---|---|
| v01 | 0001~0150 | 인체 기관계·기관·조직·세포의 구성 계층 | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| v02 | 0151~0300 | 식물 뿌리·줄기·잎·꽃·열매·종자의 구성 | `D3F104D88CE9E937678298304FA72D6C30DC2F14EFBF8EE58C3E2F5E9F1AD4D5` |
| v03 | 0301~0450 | 동물 골격·근육·외피·감각기관의 구성 | `B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0` |
| v04 | 0451~0600 | 세포 소기관·막계·분자복합체의 구성 | `4A300DA1D3A98908D3C7755A099B0441F7FF9587ACAEABBB5734DFEC8CD25763` |
| v05 | 0601~0750 | 생태계·먹이망·서식지·물질순환의 구성 | `81E61680850661343C0E3516804571CB5241F295F7E248CB96FEB348EF7A2975` |

모든 파일은 top-level `split: train`, record `type: partwhole_packet`, record `split: train`을 사용한다. 모든 record의 primary concept는 text에 직접 나타나며, 전 record가 두 문장이다.

누적 text 분량은 65,531자, 정규식 분리 단위 14,844개다. record 길이는 최소 75자, 중앙값 87자, 평균 87.375자, 최대 110자다.

## 4. 직접 작성 범위와 자동화 경계

v04·v05의 concept와 text 300개는 source TSV에서 record별로 직접 작성했다. v04는 핵·막계·에너지 소기관·세포골격·리보솜·DNA/RNA·단백질/막 복합체로 구성 범위를 분산했다. v05는 개체군·군집·영양 단계·육상/수계 서식지·탄소/질소/인/물 순환·경관 모자이크·공생체·생태 예산을 분리했다.

자동화는 source 검증, 연속 ID와 고정 schema 포장, exact/n-gram/도입부/유사도/조사 감사에만 사용했다. 같은 문장 틀의 명사 치환, sequential replace, 저밀도 문장 복사, held-out 역참조는 사용하지 않았다.

증분 빌더는 `--write-version`으로 지정한 예약 파일만 기록한다. 앞선 확정 version은 source에서 재구성한 기대 bytes와 기존 JSON이 같을 때만 `verified_unchanged`로 통과하며, 설계서 상태가 `확정`인 version을 쓰려 하면 중단한다.

## 5. relations 통제 어휘 분포

모든 750 records는 `part_of`를 포함하고 한 record의 relations 수는 2~5개다. 통제 어휘 밖 relation 및 record 내부 동일 relation 중복은 0건이다.

| relation | v04 | v05 | v01~v05 누적 |
|---|---:|---:|---:|
| `is_a` | 2 | 3 | 17 |
| `subclass_of` | 1 | 2 | 28 |
| `part_of` | 150 | 150 | 750 |
| `classification` | 73 | 76 | 288 |
| `boundary` | 21 | 25 | 150 |
| `contrast` | 13 | 27 | 84 |
| `comparison` | 0 | 8 | 16 |
| `function` | 79 | 40 | 361 |
| `role` | 23 | 7 | 97 |
| `process` | 22 | 28 | 133 |
| `state` | 13 | 26 | 79 |
| `attribute` | 19 | 9 | 108 |
| `other` | 34 | 48 | 129 |

v04에서 `comparison`이 0인 것은 분자 구조의 구성 방향을 억지 비교 label로 채우지 않은 결과다. 필요한 비교 의미는 v05에서 실제 저장고·층·다양성 지표의 비교에만 부여했다.

## 6. `other` 상위 5개 개념 유형

아래 이름은 source 감사용 분류이며 JSON relations에는 모두 `other`만 기록한다.

| 순위 | 편집 유형 | 누적 | v04 | v05 | 대표 의미 |
|---:|---|---:|---:|---:|---|
| 1 | aggregate identity / 집합 정체성 | 45 | 16 | 14 | 소단위체 짝·고리·군집·개체군처럼 구성원을 한 집합으로 세는 경우 |
| 2 | abstract structure / 추상 구획·과정 구조 | 28 | 5 | 15 | 핵소체 구역, 먹이망 경로, 영양단계, 경관 패치처럼 물리 벽이 아닌 분할 |
| 3 | material portion / 물질적 몫 | 21 | 3 | 9 | 막 지질, 탄소·질소 풀, 물·유기물 등 재료량의 일부 |
| 4 | membership–component boundary / 구성원·구조부품 경계 | 21 | 7 | 6 | 동적 복합체 참여자, 공생자, 표본·관측망처럼 구성원과 내부 부품을 구별하는 경우 |
| 5 | provenance grouping / 공통 발생·생성 이력 묶음 | 14 | 3 | 4 | 리보솜 전구체, 소포 외피, 생물 잔재, 표지 재포획처럼 생성·관찰 이력으로 묶는 경우 |

## 7. v01~v05 누적 품질 감사

비교 대상은 현재 Stage1 (5)를 제외한 기존 고밀도 train·validation 21,700 records다. 저밀도와 held-out은 감사 기준에서도 제외했다.

| 감사 항목 | 최종 결과 |
|---|---:|
| JSON parse / UTF-8 / Unicode escape 파일 | PASS / PASS / 0 |
| 파일 / records / ID 범위 | 5 / 750 / `S1-PWH-0001`~`0750` |
| schema / metadata / ID 오류 | 0 / 0 / 0 |
| source parse / source–JSON 불일치 | 0 / 0 |
| relation 규칙 오류 | 0 |
| duplicate ID / concept / exact text / concept–relation-set | 0 / 0 / 0 / 0 |
| 기존 고밀도와 exact concept / text / concept–relation-set | 0 / 0 / 0 |
| 내부 / 기존 고밀도 교차 반복 5어절 | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 오류 | 0 |
| 실제 광역 조사 오류 | 0 |
| control / unusual character 후보 | 0 / 0 |
| 내부 최대 문자 3~5-gram TF-IDF cosine | 0.341656 |
| 기존 고밀도 대비 최대 cosine | 0.321366 |

광역 조사 후보 12건은 `맞닿는`, `가까이`, `붙잡는`, `물통로`, `잡아먹는`, `가라앉는`의 어휘 말음을 조사로 오인한 false positive다. 실제 `은/는`, `이/가` 등의 오류는 없었다.

상위 내부 유사 쌍은 일반 척주와 어류 척주, 서로 다른 육량체/고리 복합체, 극피동물과 해면의 골편, 탄소와 질소 저장고처럼 필수 전문어를 공유하지만 객체·전체·과정이 다른 사례였다. 원문을 직접 대조해 중복 문장으로 판정할 쌍이 없음을 확인했다.

v04 1차 감사의 내부 반복 표현과 v05 1차 감사의 내부·기존 고밀도 교차 5어절은 해당 source 문장을 새 어순과 표현으로 직접 다시 작성했다. 최종 내부 및 교차 5어절 반복은 모두 0건이다.

## 8. 신규 산출물 해시

| 산출물 | SHA-256 |
|---|---|
| `train/stage1_(5)partwhole_high_density_train_v04.json` | `4A300DA1D3A98908D3C7755A099B0441F7FF9587ACAEABBB5734DFEC8CD25763` |
| `train/stage1_(5)partwhole_high_density_train_v05.json` | `81E61680850661343C0E3516804571CB5241F295F7E248CB96FEB348EF7A2975` |
| `tools/stage1_relational_sources/partwhole/v04.tsv` | `DF5CD2B5C0B58BCC05FE6ED23AF21D648AD1E72FDB95C0D9D28F803EC5E1626F` |
| `tools/stage1_relational_sources/partwhole/v05.tsv` | `2A3F30B0874BC12DCF32D993429FF54DCEC134EB87702800AD078BFB8F056688` |
| `TinyLM_Stage1_PartWhole_Train_v01_v04_Progress_Audit_2026-08-31.json` | `4E7435814570CDFD9A953F1CC1CB71B6B2BB9192D63FE8AD807DE34C96BCEB5A` |
| `TinyLM_Stage1_PartWhole_Train_v01_v05_Progress_Audit_2026-08-31.json` | `9032249202E5352CE6891411F7197E48C129B0369B385F69B6E5C0A8BBEAB1B8` |

## 9. 기존 정본 보호와 재개점

이번 continuation 시작 시 고정한 Identity·Attribute·Function·Boundary train/validation 및 Part–Whole v01~v03 총 148개의 SHA-256을 종료 시 다시 계산했다. 결과는 `148/148 일치`, 변경 0, 누락 0이다. Identity 계열은 수정하지 않았다.

v04와 v05는 설계서 §9 수정 금지 원장에 새로 등록했다. 정확한 다음 작업은 다음과 같다.

```text
version: Stage1 (5) v06
ID: S1-PWH-0751 ~ S1-PWH-0900
family: 지층·암석·토양단면·유역·하천망의 구성
axes: 광물/암석, 지층/층서, 토양층위, 지류/본류, 소유역/유역
procedure: 150개 직접 작성 → v06만 기록 → v01~v06 누적 감사 → 통과 뒤 확정
```
