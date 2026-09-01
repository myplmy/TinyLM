# TinyLM Stage1 (5)~(10) train — Part–Whole v01~v03 누적 생성·감사 보고서

작성일: 2026-08-31  
정본: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`  
재개 기준: `TinyLM_Stage1_5_10_Train_Reservation_and_PartWhole_v01_Progress_Report_2026-08-31.md`  
범위: 고밀도 train만 사용. 저밀도와 held-out은 생성 source·schema 근거·concept 후보·중복/유사도 비교 대상에서 제외했다.

## 1. 이번 증분의 결론

- 중단 전 확정본인 Stage1 (5) v01 150 records를 재작성하지 않고 SHA-256으로 보호했다.
- 이번 증분에서 v02 `식물 뿌리·줄기·잎·꽃·열매·종자의 구성` 150개와 v03 `동물 골격·근육·외피·감각기관의 구성` 150개를 각각 record별로 직접 작성했다.
- 실제 JSON은 v01~v03 세 파일, 450 records이며 ID는 `S1-PWH-0001`~`S1-PWH-0450`으로 연속한다. 이번 증분의 순증가는 300 records와 2 files다.
- Stage1 (5)~(10)의 예약 총량 `14,550 records = 97 files × 150` 중 현재 진척은 `450/14,550 records`, `3/97 files`다. 잔여는 `14,100 records = 94 files`다.
- Stage1 (5) 안에서는 `450/3,450 records`, `3/23 files`가 확정되었고 잔여는 `3,000 records = 20 files`다.
- 모든 record에 `part_of`가 있으며 relations는 13개 통제 어휘만 사용했다. 한 record당 2~4개, 동일 relation 중복 0건이다.
- v01~v03 통합 감사에서 JSON/schema/metadata/ID/source 대응/relation 오류, exact 중복, 5어절 반복, 반복 도입부, 실제 조사 오류, 비정상 문자 후보가 모두 0건이었다.
- 다음 예약 지점은 v04 `세포 소기관·막계·분자복합체의 구성`, ID `S1-PWH-0451`~`0600`이다. v04 이후도 설계서 §15~§20의 97개 예약 원장을 변경하거나 재선정하지 않고 순서대로 진행한다.

이번 보고서는 97개 전체 완료 보고서가 아니라, 실제 작성·검증이 끝난 v01~v03의 재개 가능한 누적 checkpoint다.

## 2. 전체 예약과 현재 진척

| 영역 | 목표 family/file | 목표 records | 현재 확정 | 잔여 |
|---|---:|---:|---:|---:|
| (5) 부분–전체 | 23 | 3,450 | 3 files / 450 | 20 files / 3,000 |
| (6) 상태·상태 변화 | 23 | 3,450 | 0 | 23 files / 3,450 |
| (7) 공간 관계 | 16 | 2,400 | 0 | 16 files / 2,400 |
| (8) 비교·대조 | 14 | 2,100 | 0 | 14 files / 2,100 |
| (9) 문맥 통합 | 12 | 1,800 | 0 | 12 files / 1,800 |
| (10) 타입·부정·불확실성 | 9 | 1,350 | 0 | 9 files / 1,350 |
| **합계** | **97** | **14,550** | **3 files / 450** | **94 files / 14,100** |

설계서 §15~§20의 97개 family는 영역별 version·150개 ID 구간·포함 축과 함께 선예약되어 있다. 현재 확정 상태만 v01~v03으로 전진시켰으며, 나머지 family 이름과 순서는 변경하지 않았다.

## 3. 확정 파일과 concept family

| version | ID 범위 | records | concept family | 포함 축 | JSON SHA-256 |
|---|---|---:|---|---|---|
| v01 | 0001~0150 | 150 | 인체 기관계·기관·조직·세포의 구성 계층 | 기관계/기관, 기관/조직, 조직/세포, 좌우 쌍, 층·막·관 구조 | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| v02 | 0151~0300 | 150 | 식물 뿌리·줄기·잎·꽃·열매·종자의 구성 | 기관/조직, 꽃 기관, 열매/씨, 관다발, 생장점 | `D3F104D88CE9E937678298304FA72D6C30DC2F14EFBF8EE58C3E2F5E9F1AD4D5` |
| v03 | 0301~0450 | 150 | 동물 골격·근육·외피·감각기관의 구성 | 뼈/골격, 근육군, 체절, 껍질·깃·비늘, 감각 구조 | `B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0` |

세 파일은 모두 top-level `split: train`, record `type: partwhole_packet`, record `split: train` 형식이다. 각 primary concept는 해당 문장 안에 실제로 나타나며 record 내부 concept 중복은 없다. 모든 text는 두 문장이다.

텍스트 누적 분량은 40,163자, 정규식 분리 단위 9,222개다. record별 길이는 최소 75자, 중앙값 89자, 평균 89.251자, 최대 110자다.

## 4. 직접 작성과 증분 빌드 경계

v02와 v03의 primary concept와 `text`는 source TSV에서 300개 모두 개별적으로 작성했다. 같은 문장 틀의 명사 치환, sequential replace, 저밀도 문장 복사, held-out 역참조는 사용하지 않았다. 자동화는 다음 범위에만 사용했다.

- source의 150행·family·축·통제 relations·`other` 편집 분류 검증
- 연속 ID 부여와 고정 JSON schema 포장
- source와 JSON의 concept/relation/text 완전 일치 확인
- exact/n-gram/도입부/문자 3~5-gram TF-IDF 유사도/조사 후보 감사
- 기존 확정 version의 byte 비교와 보호 SHA-256 대조

증분 빌더에는 `--write-version`을 필수화했다. 설계서에서 `확정`인 version을 쓰도록 요청하면 중단하며, 목표보다 앞선 JSON은 source에서 재구성한 기대 bytes와 기존 bytes가 완전히 같을 때만 `verified_unchanged`로 통과한다. 따라서 v03 빌드 때 v01·v02는 검증만 했고 실제 쓰기는 v03 한 파일에만 수행했다.

## 5. relations 통제 어휘 분포

### 5.1 version별 분포

| relation | v01 | v02 | v03 | v01~v03 누적 |
|---|---:|---:|---:|---:|
| `is_a` | 4 | 3 | 5 | 12 |
| `subclass_of` | 14 | 6 | 5 | 25 |
| `part_of` | 150 | 150 | 150 | 450 |
| `classification` | 47 | 42 | 50 | 139 |
| `boundary` | 30 | 40 | 34 | 104 |
| `contrast` | 16 | 16 | 12 | 44 |
| `comparison` | 2 | 4 | 2 | 8 |
| `function` | 88 | 66 | 88 | 242 |
| `role` | 17 | 21 | 29 | 67 |
| `process` | 24 | 43 | 16 | 83 |
| `state` | 11 | 19 | 10 | 40 |
| `attribute` | 32 | 23 | 25 | 80 |
| `other` | 11 | 15 | 21 | 47 |

relations 개수별 record 분포는 2개 14 records, 3개 431 records, 4개 5 records다. 5개를 강제로 채운 record는 없으며, 2~5개 규칙을 모두 만족한다. 통제 어휘 밖 이름과 record 내부 동일 이름 중복은 각각 0건이다.

### 5.2 `other` 편집 유형 상위 5개

아래 유형명은 사람이 `other`의 의미를 감사하기 위한 source 전용 분류다. JSON `relations`에는 유형명을 노출하지 않고 `other`만 기록했다.

| 순위 | 누적 편집 유형 | 누적 횟수 | v03 횟수 | 대표 개념 유형 |
|---:|---|---:|---:|---|
| 1 | aggregate identity / 집합 정체성 | 15 | 8 | 좌우 쌍, 두 엽, 여러 개체·부품을 한 기능 집합으로 묶는 경우 |
| 2 | material portion / 물질적 몫 | 9 | 6 | 각질·연골·젤라틴층 등 재료 몫과 구조 전체의 관계 |
| 3 | abstract structure / 추상 구획·과정 구조 | 8 | 4 | 체구역·골격 구획·표면 지도처럼 실제 절개선이 아닌 분할 |
| 4 | membership–component boundary / 구성원·구조부품 경계 | 8 | 2 | 근육 쌍·수용/지지 구조처럼 구성원 집합과 내부 부품을 구별하는 경우 |
| 5 | provenance grouping / 공통 발생·생성 이력 묶음 | 7 | 1 | 성장고리처럼 생성 이력이 같지만 분리 부품은 아닌 경우 |

`other`가 많은 것은 오류로 취급하지 않았고, 12개 구체 relation을 억지로 부여하면 의미가 거짓이 되는 경우에만 사용했다.

## 6. v01~v03 통합 품질 감사

비교 corpus는 현재 Stage1 (5)를 제외한 기존 고밀도 train·validation 21,700 records다. 저밀도와 held-out은 포함하지 않았다.

| 감사 항목 | 결과 |
|---|---:|
| JSON parse / UTF-8 / Unicode escape 파일 | PASS / PASS / 0 |
| 파일 수 / record 수 / ID 범위 | 3 / 450 / `S1-PWH-0001`~`0450` |
| schema / metadata / ID 연속성 오류 | 0 / 0 / 0 |
| source parse / source–JSON 불일치 | 0 / 0 |
| 통제 relation·개수·중복 오류 | 0 |
| duplicate ID / primary concept / exact text | 0 / 0 / 0 |
| 내부 duplicate concept–relation-set | 0 |
| 기존 고밀도와 exact primary / exact text / exact concept–relation-set | 0 / 0 / 0 |
| 내부 / 기존 고밀도 교차 반복 5어절 | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| primary concept 직후 조사 오류 | 0 |
| 실제 광역 조사 오류 | 0 |
| control character / unusual character 후보 | 0 / 0 |
| 내부 최대 문자 3~5-gram TF-IDF cosine | 0.342318 |
| 기존 고밀도 대비 최대 cosine | 0.320477 |

광역 조사 후보는 7건이었다. `맞닿는` 5건, `가까이` 1건, `붙잡는` 1건의 마지막 음절을 탐지기가 조사로 오인한 false positive였으며, `은/는`, `이/가` 등의 실제 오류는 없었다.

내부 유사도 상위 쌍은 사람이 원문을 다시 확인했다. 최고 쌍은 일반 척주와 어류 척주의 구성 차이, 둘째는 극피동물 골편과 해면 골편의 서로 다른 골격 체계, 셋째는 옆줄과 달팽이관에서 털세포가 맡는 서로 다른 감각 맥락이다. 공유 전문어 때문에 표면 유사도가 올라갔지만 객체·전체·기능 경계가 달라 중복 문장으로 판정하지 않았다. 기존 고밀도와의 최고 쌍도 `혈액과혈장구성`과 Identity의 `혈장`으로, 동일 문장·동일 객체–relation 조합이 아니었다.

v03 1차 감사에서는 `젤状`의 한자 혼입 1건을 잡았다. source의 해당 표현을 `젤라틴성`으로 직접 수정하고 v03만 재빌드한 뒤 전체 감사를 다시 실행했다. 최종 unusual character 후보는 0건이다.

## 7. 해시와 재현 산출물

| 산출물 | SHA-256 |
|---|---|
| `train/stage1_(5)partwhole_high_density_train_v01.json` | `BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A` |
| `train/stage1_(5)partwhole_high_density_train_v02.json` | `D3F104D88CE9E937678298304FA72D6C30DC2F14EFBF8EE58C3E2F5E9F1AD4D5` |
| `train/stage1_(5)partwhole_high_density_train_v03.json` | `B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0` |
| `tools/stage1_relational_sources/partwhole/v01.tsv` | `DE3F698E474E35D18DAE4978138C2CA6088EB923761E8EA1FC371CF4BCF2DD51` |
| `tools/stage1_relational_sources/partwhole/v02.tsv` | `75BD86ECF0ACF6507B74286442A3E90B8ECFDDB56401FF758EDA928CA289F917` |
| `tools/stage1_relational_sources/partwhole/v03.tsv` | `CE20BBF4E4DBAACFA04D0F54F4956C0814C90FD1D8E58FA2760FADBF0058A0E1` |
| `TinyLM_Stage1_PartWhole_Train_v01_v03_Progress_Audit_2026-08-31.json` | `AC42EC84FD90C1B7B3103C3AC8B89959F5E2D4D7B31C54B14892CA8379BBFCDE` |

패키저는 `tools/build_stage1_relational_train.py`, 감사기는 `tools/audit_stage1_relational_train.py`다. JSON을 직접 재직렬화하지 않고 직접 작성 source를 정본 입력으로 삼는다.

## 8. 기존 정본 보호 결과

이번 증분 시작 시 Identity·Attribute·Function·Boundary train/validation과 Part–Whole v01을 포함한 기존 정본 146개의 SHA-256을 고정했다. 종료 시 다시 계산한 결과는 `146/146 일치`, 변경 0, 누락 0이다. 특히 `stage1_(1)identity_high_density_*` 계열은 전혀 수정하지 않았다.

새로 확정한 v02·v03은 설계서 §9 수정 금지 원장에 추가했다. 이후 작업에서 이 두 파일도 기존 v01과 동일하게 byte 보존 대상으로 취급한다.

## 9. 정확한 재개 지점

```text
다음 version: Stage1 (5) v04
ID: S1-PWH-0451 ~ S1-PWH-0600
concept family: 세포 소기관·막계·분자복합체의 구성
포함 축: 핵·막·소기관, 세포골격, 리보솜, 단백질 복합체, 분자 하위단위
목표: 직접 작성 150 records → v04 단독 쓰기 → v01~v04 누적 전수 감사
```

v04가 150행·schema·통제 relations·중복·유사도·조사·고밀도 분리 감사까지 통과하기 전에는 설계서 상태를 `확정`으로 바꾸지 않는다. Stage1 (5) v23을 끝낸 다음에만 Stage1 (6) v01로 이동한다.
