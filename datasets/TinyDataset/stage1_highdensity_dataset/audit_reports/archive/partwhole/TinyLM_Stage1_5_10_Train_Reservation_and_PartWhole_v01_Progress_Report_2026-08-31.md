# TinyLM Stage1 (5)~(10) train 개념군 예약 및 Part–Whole v01 착수 감사 보고서

작성일: 2026-08-31  
정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`  
밀도 범위: 고밀도 train만 사용. 저밀도·held-out은 생성 및 중복 비교 기준에서 제외했다.

## 1. 결론

- Stage1 (5)~(10)의 사용자 지정 총량 `14,550 records = 97 files × 150`에 대응하는 concept family 97개를 설계서 §15~§20에 선예약했다.
- 영역별 예약 수는 (5) 23개, (6) 23개, (7) 16개, (8) 14개, (9) 12개, (10) 9개다. 버전·ID 범위·family·포함 축·상태를 한 행으로 고정해 context 압축이나 재개 시 재선정하지 않도록 했다.
- 기계 점검 결과 97개 family 이름은 97개 모두 고유하고, 영역별 버전은 v01부터 목표 끝 버전까지 연속이며, 모든 ID 예약 범위는 150개 단위로 끊긴다. 합계도 14,550 records와 일치한다.
- 생성은 예약 순서대로 Stage1 (5) v01부터 시작했다. 현재 확정 산출물은 `stage1_(5)partwhole_high_density_train_v01.json` 한 파일, 150 records다.
- 현재 전체 진척은 `150/14,550 records`, `1/97 files`이고 잔여는 `14,400 records`, `96 files`다. Stage1 (5) 안에서는 `150/3,450`, 잔여 `3,300 records = 22 files`다.
- 이번 단계에서는 Stage1 (6)~(10)의 JSON을 미리 만들지 않았다. 예약 원장에 고정된 순서를 유지해 다음 작업은 Stage1 (5) v02에서 재개한다.

## 2. 예약 원장 검증

| 영역 | 설계서 원장 | 파일 수 | record 수 | 첫/끝 버전 | 첫/끝 ID | family 이름 중복 |
|---|---:|---:|---:|---|---|---:|
| (5) 부분–전체 | §15 | 23 | 3,450 | v01~v23 | S1-PWH-0001~3450 | 0 |
| (6) 상태·상태 변화 | §16 | 23 | 3,450 | v01~v23 | S1-SCH-0001~3450 | 0 |
| (7) 공간 관계 | §17 | 16 | 2,400 | v01~v16 | S1-SPH-0001~2400 | 0 |
| (8) 비교·대조 | §18 | 14 | 2,100 | v01~v14 | S1-COH-0001~2100 | 0 |
| (9) 문맥 통합 | §19 | 12 | 1,800 | v01~v12 | S1-CTH-0001~1800 | 0 |
| (10) 타입·부정·불확실성 | §20 | 9 | 1,350 | v01~v09 | S1-TUH-0001~1350 | 0 |
| **합계** |  | **97** | **14,550** |  |  | **0** |

97개 이름과 각 family의 내부 축은 설계서 표가 유일한 재개 원장이다. 단순히 이름만 달리한 재사용을 피하도록 영역마다 판정 과제를 분리했다. 예를 들어 Stage1 (5)는 실제 구성 방향, Stage1 (6)은 전후 상태와 전이 조건, Stage1 (7)은 기준계가 있는 위치, Stage1 (8)은 비교 기준과 단위, Stage1 (9)는 복수 객체의 문맥 추적, Stage1 (10)은 타입·부정 범위·불확실성 판정을 담당한다.

공간 관계에는 13개 어휘 안에 전용 label이 없으므로 `other`를 의무화했다. 타입·부정·불확실성도 전용 이름을 만들지 않고 `other`와 의미상 필요한 `classification`·`boundary`·`state`를 조합하도록 등록했다. source의 세부 편집 유형과 논리 패턴은 감사용 metadata이며 JSON의 `relations` 값으로 출력하지 않는다.

## 3. Stage1 (5) v01 작성 범위

```text
파일: stage1_(5)partwhole_high_density_train_v01.json
ID: S1-PWH-0001 ~ S1-PWH-0150
type/split: partwhole_packet / train
concept family: 인체 기관계·기관·조직·세포의 구성 계층
포함 축: 기관계/기관, 기관/조직, 조직/세포, 좌우 쌍, 층·막·관 구조
records: 150
text: 13,740자 / 정규식 분리 단위 3,157개
길이: 최소 79자 / 중앙값 92자 / 평균 91.600자 / 최대 110자
문장 수: 전 record 2문장
```

150개 `text`는 source TSV에서 각각 직접 작성했다. 자동화는 TSV의 행 수·통제 어휘·family·ID 범위·문자열 일치 검증과 JSON 포장에만 사용했다. 사람 검토에서 부분 방향이 애매할 수 있던 속귀/전정기관, 큰침샘/분비관, 어깨관절 복합체/회전근개, 연막/연막세포 사례를 더 엄밀한 구성 관계로 수정한 뒤 다시 빌드하고 감사했다.

## 4. relations 통제 어휘 분포

모든 record는 `part_of`를 포함한다. 한 record의 relations 수는 2~5개이고 동일 이름의 중복 및 통제 어휘 밖 이름은 0건이다.

| relation | 횟수 |
|---|---:|
| `is_a` | 4 |
| `subclass_of` | 14 |
| `part_of` | 150 |
| `classification` | 47 |
| `boundary` | 30 |
| `contrast` | 16 |
| `comparison` | 2 |
| `function` | 88 |
| `role` | 17 |
| `process` | 24 |
| `state` | 11 |
| `attribute` | 32 |
| `other` | 11 |

`other` 11건의 편집 유형 상위 5개는 다음과 같다. 아래 이름은 source 감사 분류이며 JSON relation 이름이 아니다.

| 순위 | `other` 편집 유형 | 횟수 | 대표 concept |
|---:|---|---:|---|
| 1 | aggregate identity: 좌우 기관을 한 쌍으로 세는 집합 정체성 | 4 | 두콩팥과한쌍구성, 두폐와한쌍구성 |
| 2 | membership–component boundary: 구성원·공간·물질과 구조 부품의 경계 | 3 | 손목뼈와여덟뼈구성, 관모양기관과벽내강구성 |
| 3 | abstract structure: 실제 막이 아닌 해부학적 구획 | 2 | 종격과기관배치구성, 복부사분면과장기위치구성 |
| 4 | material portion: 물질적 몫과 전체의 구분 | 1 | 혈액과혈장구성 |
| 5 | provenance grouping: 현재 구조와 공통 발생 기원의 구분 | 1 | 중추신경계와신경관유래구조구성 |

논리 패턴 분포는 `hierarchical_subunit` 58, `structural_component` 59, `membership_collection` 19, `material_composition` 8, `noninheritance_boundary` 6이다. 이 값도 source 감사용이며 출력 schema를 확장하지 않는다.

## 5. 품질 감사

비교 범위는 현재 영역을 제외한 기존 고밀도 train·validation JSON 21,700 records다.

| 감사 항목 | 결과 |
|---|---:|
| JSON parse / UTF-8 / Unicode escape 파일 | PASS / PASS / 0 |
| top-level·record schema 오류 | 0 |
| metadata·ID 연속성 오류 | 0 |
| source–JSON 불일치 | 0 |
| relation 규칙 오류 | 0 |
| duplicate ID / primary concept / exact text | 0 / 0 / 0 |
| 내부 duplicate concept–relation-set | 0 |
| 기존 고밀도와 exact concept / exact text / exact concept–relation-set 교집합 | 0 / 0 / 0 |
| 내부 / 기존 고밀도 교차 반복 5어절 | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 오류 | 0 |
| control / 비정상 문자 후보 | 0 / 0 |
| 내부 최대 문자 3~5-gram TF-IDF cosine | 0.243038 |
| 기존 고밀도 대비 최대 cosine | 0.320526 |

문장 전체의 광역 조사 탐지 후보는 4건이었다. 네 항목 모두 동사 관형형 `맞닿는`의 끝 음절을 조사로 잘못 인식한 false positive였으며 실제 `은/는`, `이/가` 등의 오류는 0건이다. 내부 최고 유사 쌍은 같은 시냅스의 송신부와 수신부를 의도적으로 대조한 두 레코드였고 0.243038에 그쳤다. exact 중복과 5어절 반복이 없으므로 보일러플레이트 묶음으로 판정할 근거가 없다.

## 6. 파일 해시와 재현 경로

| 산출물 | SHA-256 |
|---|---|
| `train/stage1_(5)partwhole_high_density_train_v01.json` | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| `tools/stage1_relational_sources/partwhole/v01.tsv` | `DE3F698E474E35D18DAE4978138C2CA6088EB923761E8EA1FC371CF4BCF2DD51` |
| `TinyLM_Stage1_PartWhole_Train_v01_Progress_Audit_2026-08-31.json` | `F9804891DA1254AA7198F020CB27C9B24CBC1B1F5EA7FA9AAC95D61BCF39ADAC` |

패키저는 `tools/build_stage1_relational_train.py`, 감사기는 `tools/audit_stage1_relational_train.py`다. 실제 문장 원천은 TSV이고, JSON을 직접 손으로 재직렬화하지 않는다.

작업 시작 시 고정한 Identity·Attribute·Function·Boundary 고밀도 train/validation 145개 파일의 SHA-256을 v01 작성 뒤 다시 계산했다. 시작 원장과 `145/145`가 일치했고 변경·누락 파일은 0개다. identity 계열을 포함한 기존 정본은 수정하지 않았다.

## 7. 재개 지점

다음 작업은 설계서 §15의 `v02 / S1-PWH-0151~0300 / 식물 뿌리·줄기·잎·꽃·열매·종자의 구성`이다. v02 source가 실제 150행이고 전수 감사가 통과하기 전에는 v02를 `확정`으로 바꾸지 않는다. Stage1 (5) v23까지 끝난 뒤 같은 원칙으로 Stage1 (6) v01로 이동한다.
