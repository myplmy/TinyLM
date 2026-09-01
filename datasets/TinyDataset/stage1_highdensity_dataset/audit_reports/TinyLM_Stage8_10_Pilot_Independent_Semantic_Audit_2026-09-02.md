# Stage8~10 pilot 독립 교차 의미감사 확정 보고서

> 감사일: 2026-09-02 (KST)  
> 최종 판정: **Stage8 PASS / Stage9 PASS / Stage10 PASS**  
> 독립성: 감사자는 Stage8~10 corpus의 source·JSON을 작성하거나 수정하지 않았다. 모든 교정은 원 작성자가 canonical source에서 직접 수행했고, 감사자는 교정 전후 판독과 기계 보고서 대조만 수행했다.

## 1. 감사 범위와 방법

각 Stage의 최종 4파일에서 다음 표본을 읽었다.

- 파일별 rows 1~5, 10·20·…·150, 73~77, 148~150
- validation `unseen_relation: true` 18건 전부
- 사용 relation label별 최소 1건과 유일·희소 label 전수
- 최초 지적 및 원 작성자가 보고한 모든 교정 ID
- 내부·train/validation·Stage1·peer Stage의 TF-IDF 상위 유사쌍

교정본 기준 중복 제거 직접 판독 범위는 Stage8 124건, Stage9 135건, Stage10 130건 이상이다. 검토 축은 교육목표 적합성, primary concept와 text의 정합, relation 의미, `other`의 정당성, 한국어 조사·호응·띄어쓰기, 보일러플레이트, train/validation 독립성이다.

## 2. Stage8 교정 및 재검증

최초 감사에서 조사·문장 완결성·하위 유형 의미가 약한 행과 인공 합성 primary를 지적했다. 원 작성자는 `S8-CAH-00070`, `S8-EQH-00100`, `S8-ACH-00005/00050/00077`, `S8-EQV-00002/00029/00065/00099/00116/00148`을 직접 교정했다.

추가 재검증에서는 다음을 확인했다.

- `S8-CAH-00028`: 판정 대상 미생물 개체가 공통 상위 분류군에 속한다고 명시해 `is_a`가 실제 개체→범주 관계가 됐다.
- `S8-ACH-00144`: primary와 본문을 `초식동물 감소와 포식자 증가 대안`으로 통일해 인공 결합을 없앴다.
- `S8-ACH-00077`, `S8-EQV-00065/00116/00148`: 실제 하위 유형·형식·기능·과정을 본문에 밝혀 `subclass_of/function/process` 의미를 뒷받침한다.
- validation true 18건은 미관측 **정렬 relation-set**이고 false 132건은 train 관측 set이다. 모든 validation label은 Stage8 train에 의미 있는 사례가 있다.
- train/validation 상위 유사쌍은 넓은 주제만 공유하며 동일 사건 또는 행 번호 대응형 재서술이 아니다.

판정: **PASS**.

## 3. Stage9 교정 및 재검증

최초 감사에서 `subclass_of/is_a`를 속성·부분·기능에 잘못 붙인 사례와 국소적인 합성어·역할 오표기를 지적했다. 원 작성자는 `S9-RSH-00017/00038/00057/00074/00076/00121/00131`, `S9-WSH-00010/00149`, `S9-PAH-00020/00024/00069/00077/00140/00142`를 직접 교정했다.

추가 재검증 결과는 다음과 같다.

- `S9-RSH-00057/00122`에 남은 `subclass_of` 2건은 각각 무응답의 하위 유형과 기작 질문의 하위 유형을 실제 본문에 명시한다.
- `S9-RSH-00149`: 관계를 `role`에서 `function`으로 고쳐 순서도가 선행 관계를 표시하는 기능과 일치한다.
- `S9-PAH-00020`: `원패킷`을 `원본 패킷`으로 자연화했다.
- `S9-WSH-00148`: `국가 사망 자료 조회 권한`으로 띄어쓰기와 의미 범위를 바로잡았다.
- validation true 18건·false 132건의 set 조건, 개별 label train coverage, train/validation 독립성 모두 유지됐다.

판정: **PASS**.

## 4. Stage10 교정 및 재검증

### 4.1 희소 taxonomy relation

최초 원고의 `S10-EIH-00008 is_a`와 `S10-EIH-00102 subclass_of`는 실제 유형 관계가 아니었다. 원 작성자는 억지 taxonomy label을 다른 label로 치환하지 않고 제거했으며, 현행 Stage10 train/validation에는 `is_a=0`, `subclass_of=0`이다. 이는 통제어휘 규정의 “애매하면 `other`, 거짓 label을 억지로 만들지 않는다”는 원칙과 일치한다. validation에서 사용하는 나머지 11개 label은 모두 train에 의미 있는 사례가 있다.

### 4.2 한국어·primary concept 자연화

원 작성자는 A01 train 17건, A03 train 28건, A06 train 1건, A01 validation 24건을 먼저 직접 교정했다. 이어 독립 재검증에서 발견한 validation 잔여 16건도 다음처럼 concept와 본문 literal을 함께 자연화했다.

- `S10-EIV-00004/00010/00013/00030`: 전시품 반출 과정의 책임 구조, 상속 계보에 따른 청구자 확인, 인골 반환의 여러 판단 기준, 반환 전 보존 위험 평가
- `S10-EIV-00040/00050/00060/00072`: 반환 통관을 위한 품목 분류, 식민 관청 문서의 기록 공백, 위작 의심에 따른 반환 판단 유보, 공동체 동의 절차의 통합 검증
- `S10-EIV-00075/00077/00080/00100`: 반환 유물의 연구 접근 기준, 성별에 따른 접근 규범 조정, 반환 지역의 시설 준비 상태, 반환 기념 공간의 역할
- `S10-EIV-00110/00120/00130/00149`: 발견 장소에 따른 권리 범위, 임시 압수와 반환 절차의 연계, 분쟁 재개 조항, 반환 이후의 지속적 협력 관계

`S10-EIV-00013`은 청구 유형 분류와 우선순위 비교를 본문에 직접 써 `classification/comparison`을 함께 뒷받침한다. `S10-LHH-00073/00130/00149`, `S10-MCH-00149`, `S10-EIV-00039/00055/00063`의 호응·역할 문제도 모두 해소됐다.

### 4.3 의미 중복과 train/validation 독립성

다음 의미 중복 5쌍은 각 쌍의 한쪽을 다른 판단 구조로 직접 재작성했다.

- `S10-EIH-00134` / `S10-MCH-00058`
- `S10-EIH-00130` / `S10-MCH-00016`
- `S10-EIH-00028` / `S10-EIH-00089`
- `S10-LHH-00037` / `S10-MCH-00065`
- `S10-EIV-00008` / `S10-EIV-00070`

교정본의 TF-IDF 상위쌍과 validation true 18건을 다시 읽은 결과, 동일 사건·동일 객체-관계 조합·행 번호 대응형 골격 누출은 발견하지 못했다. `other`는 법적 효력·관할, 규범 갱신, 토지 이용 규제, 기록 공백처럼 다른 12개 label로 정확히 표현하기 어려운 의미에 사용됐다.

판정: **PASS**.

## 5. 최종 기계 감사 수치

| 항목 | Stage8 | Stage9 | Stage10 |
|---|---:|---:|---:|
| records / canonical source rows | 600 / 600 | 600 / 600 | 600 / 600 |
| validation true / false | 18 / 132 | 18 / 132 | 18 / 132 |
| true set가 train에 관측됨 | 0 | 0 | 0 |
| false set가 train에 없음 | 0 | 0 | 0 |
| validation 개별 label train 누락 | 0 | 0 | 0 |
| exact text duplicate | 0 | 0 | 0 |
| 내부 5어절 반복 | 0 | 0 | 0 |
| 문장 4어절 도입부 반복 | 0 | 0 | 0 |
| Stage1 교차 5어절 | 0 | 0 | 0 |
| Stage8~10 peer 교차 5어절 | 0 | 0 | 0 |
| 실제 조사·문법 오류 | 0 | 0 | 0 |
| 보호 기준 mismatch | 0 / 371 | 0 / 371 | 0 / 371 |
| 내부 cosine 최대 | 0.198742 | 0.170729 | 0.134372 |
| train/validation cosine 최대 | 0.146771 | 0.119528 | 0.092804 |
| Stage1 교차 cosine 최대 | 0.193942 | 0.186864 | 0.230981 |
| Stage8~10 peer cosine 최대 | 0.305367 | 0.305367 | 0.181780 |

모든 cosine 값은 0.72 gate 미만이다. machine report 원본은 각 Stage의 `audit_reports/machine/TinyLM_Stage*_Pilot_Audit_2026-09-01.json`이다.

## 6. Relations 분포

| relation | Stage8 | Stage9 | Stage10 |
|---|---:|---:|---:|
| is_a | 3 | 0 | 0 |
| subclass_of | 5 | 2 | 0 |
| part_of | 160 | 140 | 108 |
| classification | 275 | 216 | 129 |
| boundary | 468 | 401 | 517 |
| contrast | 153 | 114 | 64 |
| comparison | 296 | 204 | 211 |
| function | 90 | 193 | 241 |
| role | 48 | 90 | 195 |
| process | 243 | 344 | 324 |
| state | 260 | 386 | 414 |
| attribute | 304 | 256 | 145 |
| other | 104 | 72 | 69 |

`other` 상위 5개 유형은 다음과 같다.

| Stage | 유형 5개 |
|---|---|
| Stage8 | 대안 원인 2, 관측 공백 2, 복합 원인 2, 전이 전제 1, 기록 단절 1 |
| Stage9 | 행정 허가 범위 2, 조작적 정의 1, 진단 계층 1, 응답 경로 1, 부재 추론 1 |
| Stage10 | 규범 갱신 절차 2, 제도 적용 경계 1, 재산권 조정 1, 토지 이용 규제 1, 비등록 거주 증거 1 |

## 7. 최종 파일 무결성

| Stage | 파일 | JSON SHA-256 | canonical source SHA-256 |
|---|---|---|---|
| 8 | `stage8_(1)evidence_quality_high_density_train_v01.json` | `5f6f31fe9819ca62f3252980c9dca86711a201de346f07e73f7f021af615097f` | `ab88fb9a6a609b27d0616210938982b26f5629cb8cddcbe2ba78e9fe2e321621` |
| 8 | `stage8_(1)evidence_quality_high_density_val_v01.json` | `e0709681e8a555cfae447e17b909442281fe5dd7d13390c12c368978d52ed1b9` | `004b78c3653f8da4ba95e29dae84eda8cc049bd00b750de1f5886296ee88caf4` |
| 8 | `stage8_(3)argument_critique_high_density_train_v01.json` | `333903bd0b6e2e17ee179c30c5dfc45c57bc732d28c1326f0729b9c23c655f11` | `5634576b93c59f2c1c9939de5c9ddcb30c716714a3f6ddefbbd88d12580fb328` |
| 8 | `stage8_(6)calibration_abstention_high_density_train_v01.json` | `7e6ccc64b6e82fb9416e629ca40384c53355cce246c8529cc1ec11218b17a8ce` | `94d810e51e2ab5a351458e7907c8c0011b1158cdbef6bdd8989935f3589a6ee0` |
| 9 | `stage9_(1)research_synthesis_high_density_train_v01.json` | `a863c7c6f55788f7c54c3c7b8d1b31df1bde862fef534eab28b2e3d7f2681f90` | `59f7d4b3d4de43717cf6f9ba54f87d191a6523c2f1a32d144aaf89e2db4ddcdb` |
| 9 | `stage9_(1)research_synthesis_high_density_val_v01.json` | `d99cf120fe8ef12aae92561cf9da606637197f2370273f4be66d814d159b2b31` | `1a7103c1ab363a35df32f10943786370ba81fabf09dd2099af7d34afb34e4cc2` |
| 9 | `stage9_(3)workflow_state_high_density_train_v01.json` | `5ebdb9f908aafbde8d51d0f8c42178a463828e6882b82c0436fb142b0f9758ff` | `72deef989c6152a8874b665a5a659b986e4bc5b3a3bfff66deb9e4168702c315` |
| 9 | `stage9_(6)provenance_audit_high_density_train_v01.json` | `a996f6c0675c4d8ed0ebb93e2ba6e0371cc4959334597593272a1cd00a935f01` | `17455139c4d3deba88ce214c71c34d13fc20e30602ffeeeebc59d10de382a1a1` |
| 10 | `stage10_(1)expert_integration_high_density_train_v01.json` | `268c1f3f4164403039ad675a6b9fe4f4edc5a0cbcab65db1680c42bb1023ca9c` | `4da5c29dcbd798a0801f290235c78b2efb7de3b3ec217bd4d5e07bf50ce97bce` |
| 10 | `stage10_(1)expert_integration_high_density_val_v01.json` | `ff33bb90d3acf2d96d8001d7a94d1b623a1428f64b4fbada1f5c1d39fc615e3e` | `326ac4f4b7c5f8c66905f787110a31e714959b7538449c6f8d116904f0e8b5a0` |
| 10 | `stage10_(3)long_horizon_high_density_train_v01.json` | `305c247ac34ded578886f4268ed7864e02ab888d474b7661e370717254fe4351` | `85c690c6dac0dd63f9591c7e618e6959237cd8057eb5b65584548b1cbf247241` |
| 10 | `stage10_(6)metacognitive_control_high_density_train_v01.json` | `6e0e4c0da1e780a50d7b5ce3fbbf355e9b9a858c6680d152729c3015259b141d` | `30849014c0b59549968857f8618bfd4208bb12bbbfe01de563d46132aa263b74` |

## 8. 결론

Stage8~10의 12개 pilot 파일은 교정본 기준으로 교육목표·concept/text·relations·한국어·validation 분리·중복/유사도·보호 무결성 gate를 모두 통과했다. 미해결 지적은 **0건**이며, 독립 감사 과정에서 corpus/source/JSON을 수정한 건수도 **0건**이다.
