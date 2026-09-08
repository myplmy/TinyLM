# TinyLM Stage 1~Stage 10 데이터셋 설계서·확정 원장

- 문서 상태: 현행 설계·이력 정본
- 기준일: 2026-09-02 KST
- 대상 프로젝트: 약 100M 파라미터급 한국어 TinyLM curriculum
- 짝 문서: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`

이 문서는 특정 데이터셋의 설계 방향, token·record 배분, ID 범위, 미리 선정한 concept family, 생성·감사 이력, 확정 산출물과 수정 금지 범위를 보존하는 원장이다. 범용 생성·검증 규칙은 짝 문서인 작업지침서를 따른다. 새 작업은 두 문서를 모두 읽어야 하며, 상태가 충돌하면 **실제 파일 → 최신 감사 JSON → 이 설계서 → 작업지침서 → 과거 handoff** 순으로 판정한다.

파일명은 기존 링크와 자동화 호환성을 위해 `Stage1_Stage7`을 유지하지만, 본문 설계 범위는 Stage 1~10이다.

## 1. 지침서 이관 범위와 무손실 매핑

2026-08-31 분리 전 작업지침서의 특정 이력은 다음 위치로 이관했다.

| 분리 전 지침서 범위 | 이 설계서 위치 | 이관 내용 |
|---|---|---|
| Stage 1~10 역할, Stage 1 3M mixture | §2~§3 | curriculum 역할·배분·영역별 목적 |
| Identity 현행 snapshot | §4 | 파일·record·ID·legacy 주의·family 누적 |
| Attribute train 현행 상태 | §5 | 목표량·v01~v31 family·감사 결과 |
| Attribute validation 확정 상태 | §6 | 목표량·family·unseen 해석·감사 결과 |
| Function train 목표·27개 예약표·감사 | §7 | 의미 범위·ID·family·분포·산출물 |
| Function validation 목표·3개 family·감사 | §8 | 분리 방식·분포·other 유형·산출물 |
| 수정 금지 구체 목록·현재 산출물 | §9~§10 | 보호 pattern·감사/빌더/원고 목록 |
| 새 세션 현재 재개 상태 | §11 | 완료·진행·다음 작업 상태 |
| Stage1 (4) 신규 설계·31개 예약표 | §12 | boundary schema·ID·family·상태 원장 |
| Stage1 (5)~(10) 신규 train 설계·97개 예약표 | §14~§20 | 신규 slug·ID·필수 관계·family·생성 상태 원장 |
| Stage 2~10 교육영역·3M 준비 배분·family 예약 | §29~§39 및 별도 JSON 원장 | 세부영역 비율, train/val 파일 수, slug·prefix, 150-record family와 생성 준비 상태 |

범용 relation 규칙, JSON schema, 직접 작성 원칙, split 격리, 자동 감사 항목, 보고 양식과 작업 순서는 작업지침서에 남긴다. 이관 과정에서 완료 수치나 family 원장을 삭제하지 않고 본 문서에 보존한다.

## 2. 프로젝트 curriculum 설계

TinyLM은 단순 문장 암기보다 다음 능력을 순서대로 형성한다.

1. 대상과 개념을 식별한다.
2. 정체성, 속성, 상태, 기능, 관계를 다른 정보 유형으로 구분한다.
3. 개념 경계와 반례로 과잉 일반화를 억제한다.
4. 부분–전체, 공간, 비교, 시간, 조건 의존 관계를 조합한다.
5. 문맥 안에서 여러 개념과 관계를 동시에 유지한다.
6. 부정과 불확실성, 미관측과 비존재를 구분한다.
7. 뒤 단계에서 절차, 추론, 대화, 지시 수행, 실전 문제 해결로 확장한다.

### Stage별 상위 역할

| Stage | 상위 역할 |
|---|---|
| Stage 1 | 대상·정체성·분류, 속성, 기능, 경계, 부분–전체, 상태, 공간, 비교, 문맥, 타입·부정·불확실성의 기초 ontology |
| Stage 2 | 복합 관계·의존·인과·조건·가능성·시간적 선후·상태 전이 |
| Stage 3 | 절차·행동·목표·계획·제약·자원·선택·실패와 복구 |
| Stage 4 | 장문 참조·생략·대화 상태·질문응답·화행·암시·맥락 의존 |
| Stage 5 | 귀납·연역·반례 기반 일반화·새 조합·도메인 전이 |
| Stage 6 | 장문맥·다단계 추론·복합 제약·다중 목표·정보 통합 |
| Stage 7 | 지시 수행·다턴 대화·출력 형식·도구·안전·실전 task |
| Stage 8 | 평가·비평·근거 검증·오류 진단·수정·확신도 보정·강건성 |
| Stage 9 | 조사·도구 오케스트레이션·프로젝트 분해·상태 추적·협업·산출물 생명주기·의사결정 |
| Stage 10 | 전문가 종합·신규 문제 해결·장기 실행·통합 전이·가치·안전 판단·메타 검증 |

Stage 2~10은 2026-09-01~02 사용자 지시에 따라 세부 교육영역과 준비 원장을 설계하고, 각 Stage의 tokenizer gate용 4-file pilot을 직접 작성·감사했다. 약 3M token, train/validation 90:10, 150-record 파일 단위는 준비 기준이며 token 수와 record 수를 동일시하지 않는다. §40의 실측 배분안과 후속 전체 작업은 사용자 승인을 받았으며, 현재는 정본 Guide §10의 record별 직접 작성 방식으로 pilot 다음 corpus를 순차 생성 중이다.

## 3. Stage 1 확정 3M-token mixture

| 영역 | 비율 | token | 핵심 질문 |
|---|---:|---:|---|
| 대상·정체성·분류 | 18% | 540K | 이것은 무엇인가? |
| 속성·정도·변이 | 14% | 420K | 이것은 어떤가? |
| 기능·용도·목적 | 12% | 360K | 무엇에 사용되는가? |
| 개념 경계·반례 | 14% | 420K | 왜 다른 개념인가? |
| 부분–전체 | 10% | 300K | 무엇이 무엇의 일부인가? |
| 상태·상태 변화 | 10% | 300K | 지금 어떤 상태이며 어떻게 변하는가? |
| 공간 관계 | 7% | 210K | 어디에 있고 어떻게 배치되는가? |
| 비교·대조 | 6% | 180K | 무엇이 같고 다른가? |
| 문맥 통합 | 5% | 150K | 여러 개념이 한 상황에서 어떻게 연결되는가? |
| 타입·부정·불확실성 | 4% | 120K | 정보 타입과 확실성은 무엇인가? |
| **합계** | **100%** | **3,000K** | |

교육 우선순위 관점의 25/15/12/12/10/8/6/5/4/3 비율과 실제 3M 배분을 혼동하지 않는다. packet 수는 설계 환산이며 실제 tokenizer token 수는 tokenizer가 확정된 뒤 별도로 측정한다.

### Stage 1 영역별 교육 목적

| 영역 | 반드시 분리해 가르칠 내용 |
|---|---|
| 대상·정체성·분류 | entity, 상위·하위 범주, 유형–인스턴스, 분류 경계, 오분류 방지 |
| 속성·정도·변이 | 정적 속성, 정도, 편차, 환경·시간 변화, 민감도, 안정·회복 |
| 기능·용도·목적 | 도구의 목적, 대상의 기능, 행동의 목적, 수단과 결과 |
| 개념 경계·반례 | 반례, 인접 개념, 조건부 분류, 필요·충분조건의 직관 |
| 부분–전체 | 구성요소, 방향성, 전체 속성을 부분에 잘못 상속하는 오류 |
| 상태·상태 변화 | 열림·닫힘, 켜짐·꺼짐, 손상, 상변화, 대상과 상태의 분리 |
| 공간 관계 | 안·밖, 위·아래, 근접, 좌·우, 인접, 공간 경계 |
| 비교·대조 | 비교 기준, 공통점, 상대적 크기, 명시적 차이 |
| 문맥 통합 | 사람, 대상, 위치, 도구, 행동, 상태의 동시 유지 |
| 타입·부정·불확실성 | Entity/Attribute/Quantity/Relation/State/Action, 부정, 부재·비존재, 가능성, 미관측 |

## 4. Stage1 (1) Identity 현행 snapshot

고밀도 설계 배분은 540K 중 train 486K, validation 54K인 90:10이다. held-out은 540K에 섞지 않는다.

- train v01~v41: 41개 파일, 6,100 records, `S1-IDH-001`~`S1-IDH-6100`
- validation v01~v04: 4개 파일, 600 records, `S1-IDV-0001`~`S1-IDV-0600`
- train v01만 100개이고 v02~v41은 각 150개다.
- legacy top-level metadata와 ID padding은 균일하지 않으며 일괄 재직렬화하지 않는다.
- 누적 family: 일상 사물, 음식·조리, 의복·개인용품, 자연·생태, 과학 현상, 수학·논리, 사회·제도, 문화·언어·예술, 교육, 공학·인프라, 건강 일반, 상업·물류, 교통·지리·도시, 법률, 행정·공공서비스, 농축수산, 지식·정보·기록, 환경·기후·에너지, 건축·공간, 조직·노동, 디지털 사회, 안전·재난, 가족·인구, 재료·제품·도구, 범용 공간, 시간, 인과·조건·가능성, 집합·계층·상속, 정량, 상태전이, 관찰·증거·검증 ontology.
- 2026-09-01 사용자 승인 예외에 따라 train 41파일의 기존 필드와 원본 `relations`를 그대로 둔 채 위치 보존 1:1 투영인 `relations_controlled`만 추가했다. validation 4파일은 변경하지 않았다.
- 원본 relation type은 1,916종·17,001 token이며, 매핑 1,916개는 모두 13개 통제어휘 중 정확히 하나를 가리킨다. singleton 1,047종은 규칙대로 `other`로 보냈다.
- 최종 통제 분포: `attribute` 1,208, `boundary` 3,240, `comparison` 253, `process` 1,123, `other` 3,084, `is_a` 3,210, `state` 376, `contrast` 430, `function` 763, `classification` 1,581, `part_of` 580, `role` 243, `subclass_of` 910.
- 상위 120종과 나머지 반복형 737종을 실제 `text`·`concepts`로 대조해 의미 보정 118종을 확정했고, 판단 근거 notes 146개를 남겼다. `other` 비율은 18.1401%로 40% 상한을 통과했다. 다대일 투영과 원본 배열 길이 보존을 동시에 지키기 때문에 1,103개 legacy 레코드에서 통제 라벨 반복이 생겼으며, 이는 새 corpus의 R4를 완화한 것이 아니라 되돌릴 수 있는 위치 투영을 위한 명시적 예외다.
- 매핑 정본: `relation_mapping_identity_v1.json`. 사람용 감사: `audit_reports/Stage1_(1)_Identity_Relation_Control_Audit.md`. 기계 감사: `audit_reports/machine/TinyLM_Stage1_Identity_Relation_Control_Audit_2026-09-01.json`.
- 상태: 관계 통제 감사 PASS 후 train·validation 모두 다시 수정 금지.

## 5. Stage1 (2) Attribute train 정본

```text
전체 설계: 420K
train 설계: 약 378K = 4,650 records = 31 × 150
validation 설계: 약 42K = 600 records
ID: S1-ATH-0001 ~ S1-ATH-4650
상태: v01~v31 완료·수정 금지
```

| 버전 | ID 범위 | concept family |
|---|---|---|
| v01 | 0001~0150 | 물리·감각 속성, 크기·형상·기초 통계·활성 |
| v02 | 0151~0300 | 능력·성능·행동·효율·책임·복원 |
| v03 | 0301~0450 | 생존·성장·생태 적응·번식·이동·반응 |
| v04 | 0451~0600 | 신뢰·추론·계획·자기조절·사회 행동 |
| v05 | 0601~0750 | 언어 명료성·모호성·정중성·응집성·정보밀도 |
| v06 | 0751~0900 | 물질 속성의 환경 의존·변화율·민감도·회복률 |
| v07 | 0901~1050 | 공간·시간·환경 변화에 따른 성능과 적응폭 |
| v08 | 1051~1200 | 열화·손상·고장·복구·잔여수명 |
| v09 | 1201~1350 | 측정·평가 정확성·신뢰도·타당도·오차 |
| v10 | 1351~1500 | 자원·용량·부하·효율·한계·최적화 |
| v11 | 1501~1650 | 확률·분포·변동·극값·위험·신뢰 구간 |
| v12 | 1651~1800 | 변화 방향·속도·가속·주기·수렴·안정화 |
| v13 | 1801~1950 | 정보·데이터·신호 품질·손실·잡음·지연 |
| v14 | 1951~2100 | 상호작용·상관·결합·간섭·호환·경쟁 |
| v15 | 2101~2250 | 결정·선택·우선순위·목표·제약·전략 |
| v16 | 2251~2400 | 구조·복잡성·연결성·계층성·밀도·규모 |
| v17 | 2401~2550 | 규칙·패턴·질서·순서·불변성·일탈 |
| v18 | 2551~2700 | 역치·임계 전이·포화·응답 크기·시간 응답 |
| v19 | 2701~2850 | 관측·검출·식별·구별·추정·추적 |
| v20 | 2851~3000 | 제어·피드백·조절·목표추종·구동 보정 |
| v21 | 3001~3150 | 강건성·복원탄력성·결함허용·운영연속성 |
| v22 | 3151~3300 | 학습·적응·일반화·전이·유지·망각 |
| v23 | 3301~3450 | 접근성·사용성·가독성·인지부담·표출성 |
| v24 | 3451~3600 | 모듈성·결합·응집·상호운용·대체·재구성 |
| v25 | 3601~3750 | 가역·비가역·경로의존·이력·잔류·복귀 |
| v26 | 3751~3900 | 평형·균형·항상성·보존·유입유출 수지 |
| v27 | 3901~4050 | 투과·확산·전달·운반·흐름·차단·여과 |
| v28 | 4051~4200 | 동기화·협응·정렬·위상·타이밍·합의 |
| v29 | 4201~4350 | 운전 규모·병렬 처리·분산 운영·부하 분배 |
| v30 | 4351~4500 | 공정성·대표성·편향·포용성·형평성 |
| v31 | 4501~4650 | 설명·해석·투명성·감사·근거 문서화 |

최신 전체 감사: JSON·UTF-8·ID·metadata·schema·exact text·primary concept·5어절·4어절 도입부·조사·relations 오류/중복 모두 0, 내부 최대 문자 3~5-gram TF-IDF cosine `0.499366`.

사람용 정본: `audit_reports/Stage1_(2)_Attribute_Consolidated_Audit.md`. 기계 정본: `audit_reports/machine/attribute/TinyLM_Stage1_Attribute_Train_v01_v31_Full_Audit_2026-08-30.json`.

## 6. Stage1 (2) Attribute validation 정본

```text
설계: 약 42K = 600 records = 4 × 150
ID: S1-ATV-0001 ~ S1-ATV-0600
train 대비 record 비율: 12.90%
상태: v01~v04 완료·수정 금지
```

| 버전 | ID 범위 | 새 concept family | 일반화 축 |
|---|---|---|---|
| v01 | 0001~0150 | 토양·지질·지형·수문 반응 특성 | 물성, 공간 편차, 침식, 수분 이동, 지형 안정 |
| v02 | 0151~0300 | 식품·조리·발효·저장 품질 특성 | 관능 속성, 공정 변화, 숙성, 보존, 복원·열화 |
| v03 | 0301~0450 | 건축·실내환경·도시 미기후 특성 | 열·빛·음향·공기질·동선·공간 쾌적성 |
| v04 | 0451~0600 | 해양·연안·수생환경 특성 | 염분·탁도·파랑·퇴적·혼합·서식환경 변동 |

Attribute train에는 통제 relation 13개가 모두 있어 `unseen_relation: true`는 개별 이름이 아니라 train에 없던 정렬 relation-set 조합으로 정의했다. true 72/600=`12.00%`, false 528/600=`88.00%`, 파일별 true 18/150다. true 고유 미관측 set 12종, false 고유 관측 set 22종이다.

최종 감사: JSON·UTF-8·metadata·schema·relation 오류 0, train–val exact text·primary concept·객체–relation-set 교집합 0, 내부·교차 반복 5어절 0, 반복 도입부·조사 오류 0, 내부 최대 cosine `0.383657`, train–val 최대 `0.311535`.

Relations: `is_a` 3, `subclass_of` 4, `part_of` 49, `classification` 71, `boundary` 300, `contrast` 44, `comparison` 278, `function` 90, `role` 27, `process` 207, `state` 138, `attribute` 600, `other` 52.

`other` 편집 유형: 조건·입력 의존/영향/선택성 22, 공간·시간 집중/분포/편향 12, 구조 저항/상태 분류/형태적 기타 7, 복합 감각/물질 이동·혼합/수용 6, 잠재성/불확실성/위험 추정 5.

사람용 정본: `audit_reports/Stage1_(2)_Attribute_Consolidated_Audit.md`. 기계 정본: `audit_reports/machine/attribute/TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json`.

## 7. Stage1 (3) Function train 정본

```text
전체 설계: 360K
train 설계: 약 324K = 4,050 records = 27 × 150
ID: S1-FNH-0001 ~ S1-FNH-4050
상태: v01~v27 완료·수정 금지
```

| 버전 | ID 범위 | concept family | 포함 축 |
|---|---|---|---|
| v01 | 0001~0150 | 수동 작업·정비·제작 공구의 기능 | 체결, 파지, 절단, 성형, 마감, 타격, 인출, 천공 |
| v02 | 0151~0300 | 식재료 준비·조리·제공 기구의 기능 | 세척, 계량, 분할, 혼합, 성형, 가열, 제공 |
| v03 | 0301~0450 | 식품 보존·포장·위생·품질 관리 장치 | 냉장, 건조, 밀봉, 살균, 표시, 차단, 검사 |
| v04 | 0451~0600 | 의복·신발·착용 보호·휴대 구성품 | 체온, 충격·날씨 보호, 여밈, 지지, 수납 |
| v05 | 0601~0750 | 청소·세탁·건조·폐기물 처리 도구 | 포집, 분리, 세정, 탈수, 탈취, 압축, 배출 |
| v06 | 0751~0900 | 건물 외피·개구부·실내 마감·공간 조절 | 지지, 차폐, 채광, 출입, 단열, 방수, 흡음 |
| v07 | 0901~1050 | 급배수·위생·환기·냉난방 실내 설비 | 공급, 배출, 여과, 열교환, 압력, 순환 |
| v08 | 1051~1200 | 농림·축산·수산 생산 도구와 설비 | 토양, 파종, 관개, 급이, 보호, 수확, 어획 |
| v09 | 1201~1350 | 육상·항공·해상 교통수단과 부품 | 추진, 조향, 제동, 현가, 부양, 항법, 계류 |
| v10 | 1351~1500 | 포장·하역·운반·분류·보관 물류 장비 | 적재, 결속, 완충, 이송, 승강, 추적, 보존 |
| v11 | 1501~1650 | 제조 성형·절삭·접합·조립 생산 설비 | 주조, 압연, 절삭, 연삭, 용접, 체결, 정렬 |
| v12 | 1651~1800 | 품질검사·공정제어·설비진단·유지보수 | 검출, 비교, 피드백, 보정, 윤활, 안전 정지 |
| v13 | 1801~1950 | 도로·교량·철도·터널·배수 공공 인프라 | 하중, 통행, 선형, 배수, 환기, 충돌 방호 |
| v14 | 1951~2100 | 물 공급·하수처리·위생·자원회수 서비스 | 취수, 정수, 저장, 압송, 침전, 소독, 회수 |
| v15 | 2101~2250 | 에너지 생산·변환·저장·송배전·보호 | 발전, 변압, 정류, 축전, 개폐, 차단, 보호 |
| v16 | 2251~2400 | 전자회로·센서·신호처리·구동 부품 | 감지, 변환, 증폭, 필터링, 발진, 스위칭 |
| v17 | 2401~2550 | 컴퓨팅 처리·기억·저장·입출력 장치 | 연산, 제어, 캐시, 저장, 입력, 표시, 연결 |
| v18 | 2551~2700 | 네트워크·소프트웨어·데이터 서비스 | 주소, 라우팅, 인증, 직렬화, 검색, 동기화 |
| v19 | 2701~2850 | 통신·미디어 기록·편집·전송·표현 도구 | 촬영, 녹음, 부호화, 편집, 송수신, 재생 |
| v20 | 2851~3000 | 실험실 채취·분리·반응·계량·교정 장비 | 채취, 여과, 원심분리, 배양, 적정, 검출 |
| v21 | 3001~3150 | 의료 진단·치료·모니터링·재활 기구 | 관찰, 검사, 투약, 절개, 감시, 재활, 멸균 |
| v22 | 3151~3300 | 생물 기관·세포 구조·생태계 구성원 | 흡수, 수송, 호흡, 방어, 감각, 번식, 분해 |
| v23 | 3301~3450 | 환경 감시·오염 정화·자원 순환·복원 | 감시, 집진, 흡착, 중화, 재활용, 복원 |
| v24 | 3451~3600 | 안전·재난·보안·구조·접근성 보조 | 경보, 차단, 대피, 소화, 구조, 침입 방지 |
| v25 | 3601~3750 | 교육·학습·도서관·문서화 도구 | 설명, 연습, 평가, 색인, 인용, 버전, 검색 |
| v26 | 3751~3900 | 상업·금융·거래·고객 서비스 체계 | 가격, 주문, 결제, 정산, 신용, 환불, 상담 |
| v27 | 3901~4050 | 공공행정·법률·복지·지역사회·문화 서비스 | 신청, 심사, 허가, 권리, 돌봄, 안내, 보존 |

최종 감사: schema·metadata·ID·relations·exact ID/concept/text·5어절·도입부·실제 조사 오류 모두 0. 고밀도 Function 내부 최대 cosine `0.357568`. `text` 253,352자, 분리 단위 61,667개.

Relations: `is_a` 2, `subclass_of` 42, `part_of` 340, `classification` 187, `boundary` 526, `contrast` 10, `comparison` 224, `function` 4,050, `role` 1,036, `process` 1,144, `state` 779, `attribute` 488, `other` 0. `other` 상위 유형은 해당 없음.

사람용 정본: `audit_reports/Stage1_(3)_Function_Consolidated_Audit.md`. 기계 정본: `audit_reports/machine/function/TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json`.

## 8. Stage1 (3) Function validation 정본

```text
설계: 약 36K = 450 records = 3 × 150
ID: S1-FNV-0001 ~ S1-FNV-0450
train 대비 record 비율: 11.11%
text: 32,352자 / 분리 단위 7,967개
상태: v01~v03 완료·수정 금지
```

| 버전 | ID 범위 | 새 concept family | 일반화 축 |
|---|---|---|---|
| v01 | 0001~0150 | 천문·기상·지리 현장 관측과 방향·시간 판독 도구 | 광학, 천체 좌표·시간, 기상, 지형·수문, 방향 |
| v02 | 0151~0300 | 스포츠 경기 운영·판정·훈련·기록·안전 장비 | 신호·판정·기록, 구기·육상·체조·수상, 안전 |
| v03 | 0301~0450 | 악기 연주·조율·공명·음색·공연 보조 구성품 | 현악·관악·타악·건반 발음, 조율, 공명, 제어 |

Function train에는 `other`만 0건이었다. false 396개는 train 관측 relation-set, true 54개는 train 미관측 통제 label `other`와 미관측 relation-set을 사용했다. true는 전체·파일별 `12.00%`; true 고유 set 9종, false 고유 set 13종이다.

Relations: `is_a` 0, `subclass_of` 0, `part_of` 73, `classification` 18, `boundary` 47, `contrast` 0, `comparison` 44, `function` 450, `role` 89, `process` 74, `state` 82, `attribute` 84, `other` 54.

`other` 편집 유형: 환경·장소·규정 의존 11, 관례 해석 11, 조율 신호 11, 출처 추적 11, 사용자 맞춤 10.

최종 감사: 구조·unseen/category 오류·중복·누출·5어절·도입부·실제 조사 오류 0, 내부 최대 cosine `0.349621`, train–val 최대 `0.206182`.

사람용 정본: `audit_reports/Stage1_(3)_Function_Consolidated_Audit.md`. 기계 정본: `audit_reports/machine/function/TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json`.

## 9. 수정 금지 정본 원장

- `stage1_(1)identity_high_density_train_v01.json`~`v41.json`: 2026-09-01 승인된 positional `relations_controlled` 추가와 관계 통제 감사가 끝났으므로 기존 field·원본 `relations`·새 필드를 포함해 다시 전체 수정 금지
- `stage1_(1)identity_high_density_val_v01.json`~`v04.json`: 변경 없이 전체 수정 금지
- `stage1_(2)attribute_high_density_*` train·validation 전체
- `stage2_(2)attribute_high_density_*`와 일치하는 모든 확정 파일; 현재 경로에 없어도 pattern을 보호
- `stage1_(3)function_high_density_train_v01.json`~`v27.json`
- `stage1_(3)function_high_density_val_v01.json`~`v03.json`
- `stage1_(4)boundary_high_density_train_v01.json`~`v31.json`
- `stage1_(4)boundary_high_density_val_v01.json`~`v04.json`
- `stage1_(5)partwhole_high_density_train_v01.json`~`v23.json`
- `stage1_(6)statechange_high_density_train_v01.json`~`v23.json`
- `stage1_(7)spatial_high_density_train_v01.json`~`v16.json`
- `stage1_(8)comparison_high_density_train_v01.json`~`v14.json`
- `stage1_(9)context_high_density_train_v01.json`~`v12.json`
- `stage1_(10)type_uncertainty_high_density_train_v01.json`~`v09.json`
- `stage1_(5)partwhole_high_density_val_v01.json`~`v03.json`
- `stage1_(6)statechange_high_density_val_v01.json`~`v03.json`
- `stage1_(7)spatial_high_density_val_v01.json`~`v02.json`
- `stage1_(8)comparison_high_density_val_v01.json`~`v02.json`
- `stage1_(9)context_high_density_val_v01.json`~`v02.json`
- `stage1_(10)type_uncertainty_high_density_val_v01.json`
- held-out benchmark는 source로 사용하지 않고 열람 결과로 corpus를 고치지 않는다.

새 영역 작업은 위 정본의 시작·종료 SHA-256을 비교한다. legacy 형식이 다르다는 이유로 재직렬화하지 않는다.

## 10. 현재 감사·연속성 산출물

현재 사람용 감사 진입점은 `audit_reports/README.md`다.

```text
audit_reports/Stage1_(1)_Identity_Relation_Control_Audit.md
audit_reports/Stage1_(2)_Attribute_Consolidated_Audit.md
audit_reports/Stage1_(3)_Function_Consolidated_Audit.md
audit_reports/Stage1_(4)_Boundary_Consolidated_Audit.md
audit_reports/Stage1_(5-10)_CrossArea_Consolidated_Audit.md
audit_reports/Stage1_(5)_PartWhole_Consolidated_Audit.md
audit_reports/Stage1_(6)_StateChange_Consolidated_Audit.md
audit_reports/Stage1_(7)_Spatial_Consolidated_Audit.md
audit_reports/Stage1_(8)_Comparison_Consolidated_Audit.md
audit_reports/Stage1_(9)_Context_Consolidated_Audit.md
audit_reports/Stage1_(10)_TypeUncertainty_Consolidated_Audit.md
```

기계 판독 감사 정본은 `audit_reports/machine/` 아래에 둔다. Attribute·Function·Boundary의 현행 JSON은 각각 `machine/attribute/`, `machine/function/`, `machine/boundary/`에, 과거 진행 보고서와 교체된 감사는 `archive/<area>/`에 둔다. 생성·재감사 도구와 source는 `tools/` 아래의 영역별 builder·auditor·source 디렉터리에 보존한다.

Identity 관계 통제의 매핑·재검증 산출물은 `relation_mapping_identity_v1.json`, `tools/build_identity_relation_control.py`, `audit_reports/machine/TinyLM_Stage1_Identity_Relation_Control_Audit_2026-09-01.json`이다. Stage 2~10 준비 산출물은 `TinyLM_Stage2_Stage10_Curriculum_and_Family_Reservation_Draft.md`, `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json`, `tools/prepare_stage2_stage10_scaffold.py`, `audit_reports/machine/TinyLM_Stage2_10_Preparation_Audit_2026-09-01.json`이다. Pilot 통합 감사 정본은 `audit_reports/Stage2_Stage10_Tokenizer_Pilot_Integrated_Audit_2026-09-02.md`와 `audit_reports/machine/TinyLM_Stage2_10_Pilot_Integrated_Audit_2026-09-02.json`, 실측 배분안은 `audit_reports/machine/TinyLM_Stage2_10_Pilot_3M_Allocation_Options_2026-09-02.json`이다. 독립 의미 감사 정본은 `audit_reports/TinyLM_Stage2_4_Pilot_Independent_Semantic_Audit_2026-09-02.md`, `TinyLM_Stage5_7_Pilot_Independent_Semantic_Audit_2026-09-02.md`, `TinyLM_Stage8_10_Pilot_Independent_Semantic_Audit_2026-09-02.md`다. 2026-09-02 실측 3M 승인 이후의 증보 수치·권한 경계·미확정 항목·재개점은 `TinyLM_Stage2_Stage10_Actual3M_Expansion_Work_Ledger_2026-09-02.md`를 단일 작업원장으로 사용한다.

과거 handoff의 v18 재작성 전 상태와 삭제 예정이던 continuity summary의 v17 누적은 역사적 기록이다. 현재 상태는 실제 파일과 위 최신 감사가 기준이다.

## 11. 현재 재개 상태

- Identity train: 6,100 records의 `relations_controlled` 추가·의미 재검토·감사 PASS, 다시 수정 금지. Identity validation 600 records는 변경 없이 수정 금지
- Attribute train v01~v31, validation v01~v04: 완료·수정 금지
- Function train v01~v27, validation v01~v03: 완료·수정 금지
- Stage1 (4) Boundary train v01~v31: 4,650 records 완료·감사 통과·수정 금지
- Stage1 (4) Boundary validation v01~v04: 600 records 완료·감사 통과·수정 금지
- Stage1 (5)~(10) train: §14~§20의 97개 family, 14,550 records 전체 완료·감사 통과·수정 금지
- Stage1 (5)~(10) validation: §21~§28의 13개 신규 family, 13 files·1,950 records 완료·감사 통과·수정 금지; 각 파일 18개, 전체 234개(12.00%)를 relation-set 일반화 slice로 확정
- Stage 2~10: §29~§39의 9개 Stage·54개 세부영역, primary 2,250 family와 contingency 225 family 예약 및 폴더 scaffold 준비 완료. 각 Stage의 A01·A03·A06 train v01과 A01 validation v01을 직접 작성하여 36 files·5,400 records의 tokenizer-gate pilot을 완료했다.
- Pilot은 통합 기계 감사와 세 구간 독립 의미 감사에서 모두 PASS다. 2026-09-02 사용자는 `tok-ko-en-32768.json` 기준 Stage별 약 3M안, 총 4,370 files·655,500 records를 승인했다.
- Stage 2~10 후속 승인 실행: Stage5~7 `relation_focus` whitelist 강제 제거·재감사 PASS, contingency 225개 배치와 신규 family 1,895개 선정 완료, 중앙 schema 2.0 원장 4,370행과 9개 manifest exact projection 감사 PASS
- 실제 corpus: 기존 pilot을 보존하면서 Stage2 A01 train 87 files, A02 train 86 files, A03 train 69 files를 영역별 일괄 감사·수정·포장했다. 다른 Stage pilot을 포함한 현행 완료량은 276 source/corpus pairs·41,400 records이며 중앙 예약 4,370 files 중 잔여는 4,094 files다. 현행 Stage2 train checkpoint는 A01+A02+A03 242 entries다.
- 일시중단 source였던 `S2-A01-T-039`은 사용자 재개 승인 뒤 99번째부터 남은 52행을 직접 보충했다. 완성 150행과 corpus·checkpoint를 전수 감사해 PASS로 확정했으며 중단 전 98행은 그대로 보존했다.
- 교육영역 batch 전환 뒤 Stage2 A01 train 87 files·13,050 records, A02 train 86 files·12,900 records, A03 train 69 files·10,350 records를 차례로 일괄 감사·수정·포장해 모두 PASS했다. A01 validation `S2-A01-V-002~009`는 Stage2 A02~A06 train 전체 완결 뒤로 유지하며, 현행 다음 직접 작성 대상은 A04 `S2-A04-T-001~069`이다.

## 12. Stage1 (4) 개념 경계·반례 train 설계 원장

### 12.1 목표·schema·의미 경계

```text
Stage 1 영역: (4) 개념 경계·반례
전체 설계량: 420K
train 설계량: 약 378K
train 목표: 4,650 records = 31 files × 150
validation 설계량: 약 42K; 현재 §13의 600 records·v01~v04 생성과 감사까지 완료
파일명: stage1_(4)boundary_high_density_train_v01.json ... v31.json
ID: S1-BNH-0001 ... S1-BNH-4650
type: boundary_packet
split: train
```

한 record는 겉보기 공통점만으로 두 개념을 동일시하는 오류, 흔한 속성을 필요조건으로 바꾸는 오류, 한 사례를 전체 범주로 과잉 일반화하는 오류를 실제 반례와 판정 기준으로 교정한다. 단순히 두 대상의 특징을 나열하는 비교 corpus가 아니라 **어떤 단서가 분류에 충분하지 않은지, 무엇이 결정 기준인지, 어떤 조건에서 예외가 되는지**를 가르친다.

모든 record는 `boundary`를 반드시 포함하고 통제 어휘 중 의미가 실제로 서술된 1~4개를 더해 2~5개로 구성한다. `concept_boundary`, `attribute_vs_category`, `necessary_condition` 같은 자유 label을 metadata에 만들지 않고 `boundary`, `classification`, `contrast`, `attribute`, `state`, `other` 등 통제 어휘로만 보수적으로 표현한다.

Boundary record의 `concepts`는 `[primary boundary concept, 판정에 필요한 관련 concept...]` 형식을 허용한다. 첫 항목은 split 전체에서 고유하고 `text`에 그대로 나타나야 한다. 보조 concept는 실제 문장에 등장하며 record 안에서 중복하지 않는다.

예시:

```json
{
  "id": "S1-BNH-0001",
  "type": "boundary_packet",
  "split": "train",
  "text": "비행능력과조류분류는 같은 기준이 아니다. 박쥐는 날지만 포유류이므로 비행은 조류 판정의 충분조건이 될 수 없다.",
  "concepts": ["비행능력과조류분류", "박쥐", "조류", "포유류"],
  "relations": ["boundary", "classification", "contrast"]
}
```

이 영역의 생성 근거는 고밀도 작업지침서와 본 설계서만이다. 다른 밀도의 데이터셋을 예시·중복 비교·문장 source·schema 근거로 사용하지 않는다. held-out도 생성 source나 교정 근거로 보지 않는다.

### 12.2 31개 확정 concept family

아래 표는 context 압축이나 세션 중단 뒤에도 family가 재선정·중복되지 않게 하는 고정 원장이다. 2026-08-31 원고·JSON·통합 감사가 모두 끝나 전 항목을 `확정`했다.

| 버전 | ID 범위 | 확정 concept family | 포함 경계·반례 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 동물 분류·형태·행동의 경계 | 조류/포유류, 어류/해양포유류, 곤충/거미류, 수렴 형질, 생활사 | 확정 |
| v02 | 0151~0300 | 식물·균류·조류·미생물 분류 경계 | 식물/균류, 이끼/지의류, 종자/포자, 세균/바이러스, 발효 미생물 | 확정 |
| v03 | 0301~0450 | 생태계·서식지·행동·관계의 경계 | 서식/소유, 포식/청소, 공생/기생, 토착/외래, 개체/군집 | 확정 |
| v04 | 0451~0600 | 인체 해부·생리·생체 신호 경계 | 기관/조직, 구조/기능, 정상 변이, 반사/의지, 지표/원인 | 확정 |
| v05 | 0601~0750 | 증상·질환·검사·치료·예방 경계 | 증상/진단, 위험요인/원인, 선별/확진, 치료/완화, 부작용 | 확정 |
| v06 | 0751~0900 | 식재료·음식·조리·발효·보존 경계 | 원료/요리, 생/익힘, 발효/부패, 냉장/냉동, 맛/안전 | 확정 |
| v07 | 0901~1050 | 재료·물질·혼합물·제품·제조 경계 | 원소/화합물/혼합물, 천연/합성, 재료/제품, 가공/재활용 | 확정 |
| v08 | 1051~1200 | 물리량·측정·힘·에너지·파동 경계 | 질량/무게, 열/온도, 속력/속도, 힘/에너지, 소리/파동 | 확정 |
| v09 | 1201~1350 | 화학종·결합·용액·반응 경계 | 원자/이온/분자, 산/염기, 용해/반응, 촉매/반응물, 평형 | 확정 |
| v10 | 1351~1500 | 지질·기상·수문·해양 현상 경계 | 암석/광물, 날씨/기후, 구름/안개, 조석/파랑, 침식/풍화 | 확정 |
| v11 | 1501~1650 | 천문·우주·관측 개념 경계 | 별/행성/위성, 유성/운석, 성운/은하, 겉보기/물리 운동 | 확정 |
| v12 | 1651~1800 | 수·연산·대수·함수 개념 경계 | 수/숫자, 소수/합성수, 식/방정식, 함수/관계, 값/해 | 확정 |
| v13 | 1801~1950 | 도형·공간·측정·기하 경계 | 선/선분/직선, 합동/닮음, 둘레/넓이, 원/구, 평행/수직 | 확정 |
| v14 | 1951~2100 | 확률·통계·표본·데이터 해석 경계 | 가능성/확률, 평균/중앙값, 상관/인과, 표본/모집단, 이상치 | 확정 |
| v15 | 2101~2250 | 논리·집합·조건·인과·추론 오류 경계 | 필요/충분, 참/타당, 부정/역, 원인/조건, 반례/예외 | 확정 |
| v16 | 2251~2400 | 언어·문법·의미·화용 경계 | 단어/형태소, 문장/발화, 동음/다의, 사실/함축, 인용/주장 | 확정 |
| v17 | 2401~2550 | 문서·정보·미디어·장르 경계 | 데이터/정보, 원본/사본, 기사/광고, 사실/의견, 요약/인용 | 확정 |
| v18 | 2551~2700 | 컴퓨팅·소프트웨어·데이터·네트워크 경계 | 파일/폴더, 메모리/저장, 프로그램/프로세스, 인증/권한, 오류/공격 | 확정 |
| v19 | 2701~2850 | 전기·전자·기계·제어 시스템 경계 | 전압/전류, 센서/액추에이터, 기어/축, 제어/전원, 고장/상태 | 확정 |
| v20 | 2851~3000 | 건축·건설·도시 기반시설 경계 | 구조/마감, 벽/칸막이, 보/기둥, 도로/차로, 배수/하수 | 확정 |
| v21 | 3001~3150 | 생활도구·가전·의복·개인용품 경계 | 도구/장난감, 용기/내용물, 가전/설비, 의복/보호구, 기능/장식 | 확정 |
| v22 | 3151~3300 | 교통·이동·항법·물류 경계 | 차량/운송수단, 도로/노선, 정차/주차, 화물/수하물, 위치/방향 | 확정 |
| v23 | 3301~3450 | 예술·음악·공연·시각디자인 경계 | 작품/복제, 장르/기법, 음/소음, 연주/녹음, 상징/표지 | 확정 |
| v24 | 3451~3600 | 스포츠·게임·경기 규칙 경계 | 경기/놀이, 선수/심판, 반칙/실수, 득점/기록, 장비/시설 | 확정 |
| v25 | 3601~3750 | 교육·학습·평가·연구·출판 경계 | 학습/암기, 평가/측정, 가설/결론, 인용/표절, 검토/승인 | 확정 |
| v26 | 3751~3900 | 법률·권리·의무·절차·증거 경계 | 법/규칙, 범죄/불법행위, 계약/약속, 권리/허가, 증거/주장 | 확정 |
| v27 | 3901~4050 | 정부·정책·행정·공공서비스 경계 | 국가/정부, 정책/법률, 허가/신고, 공공/민간, 권한/책임 | 확정 |
| v28 | 4051~4200 | 경제·회계·금융·상거래 경계 | 가격/가치, 수입/이익, 자산/비용, 신용/현금, 주문/계약 | 확정 |
| v29 | 4201~4350 | 사회관계·가족·조직·문화 경계 | 역할/정체성, 가족/가구, 집단/조직, 관습/규범, 협력/동조 | 확정 |
| v30 | 4351~4500 | 지리·영토·환경·기후·에너지 경계 | 장소/공간, 국경/행정구역, 자원/매장량, 날씨/기후, 재생/저탄소 | 확정 |
| v31 | 4501~4650 | 시간·상태·정체성·부정·불확실성 경계 | 대상/상태, 변화/교체, 부재/비존재, 미관측/없음, 가능/사실 | 확정 |

### 12.3 누적·상태 갱신 규칙

각 파일은 실제 150개, 선언 ID 범위, family 일치, 전수 감사 통과 뒤에만 확정한다. 갱신 시 SHA-256, 전체 누적/잔여, 13개 relations 분포, `other` 상위 5유형, duplicate·5어절·도입부·유사도·조사 결과를 기록한다. 중단 재개 시 마지막 `확정` 파일 다음 버전부터 시작하고 예약 family를 재선정하지 않는다.

### 12.4 2026-08-31 생성·수정·최종 감사 이력

```text
상태: v01~v31 확정·수정 금지
파일/record: 31 files × 150 = 4,650 records
ID: S1-BNH-0001 ~ S1-BNH-4650
text: 423,235자 / 정규식 분리 단위 103,517개
길이: 최소 51자 / 중앙값 80자 / 평균 91.018자 / 최대 176자
원문: tools/boundary_sources/v01.tsv ... v31.tsv
패키징: tools/build_boundary_train.py
감사: tools/audit_boundary_corpus.py
```

PC 중단 뒤 실제 원문·JSON·ID를 먼저 대조했고, 중단 전에 끝난 v01~v23과 v24의 선작성 75개를 보존한 채 v24 잔여 75개 및 v25~v31을 이어 작성했다. 이후 4,650개 전체를 다시 패키징하고 두 차례 의미·형식 감사를 수행했다. 1차 감사에서 발견한 실제 오탈자·조사 오류와 55개 내부 반복 5어절을 원문에서 고쳤다. 최고 유사 쌍의 `매개와교란`, `역인과와피드백`은 각각 `매개경로와효과수정`, `피드백순환과일방향경로`로 비교 축을 다시 설계했다. 2차 고밀도 교차 감사에서 남은 공유 5어절 15개도 Boundary 원문만 재작성해 제거했다.

Relations 전체 분포는 다음과 같다.

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| `is_a` | 7 | `subclass_of` | 90 |
| `part_of` | 382 | `classification` | 1,622 |
| `boundary` | 4,650 | `contrast` | 187 |
| `comparison` | 435 | `function` | 881 |
| `role` | 264 | `process` | 1,262 |
| `state` | 1,897 | `attribute` | 962 |
| `other` | 1,311 |  |  |

`other` 1,311건의 편집상 상위 5유형은 증거·추론 범위 461건, 표현–지시대상 간극 356건, 규범·권한 범위 314건, 문맥·관례 의존 137건, 필요·충분 논리 43건이다. 대표 concept는 각각 `검출불가와부재`, `먹이사슬과실제먹이망`, `권고와법적의무`, `과일과열매`, `한증상과한진단`이다.

최종 통합 감사 결과 schema·metadata·ID·source↔JSON·통제 relation 오류가 모두 0건이며 exact ID·primary concept·text·concept–relation-set 중복도 모두 0건이다. 내부/기존 고밀도 교차 5어절 반복과 4어절 도입부 반복은 0건이다. 1차 조사 후보에서 고친 실제 오류 뒤 primary concept 조사 오류는 0건이고, 광범위 탐지 79건은 전수 문맥 확인 결과 어간·명사를 조사 결합으로 잘못 잡은 false positive였다. 내부 최대 문자 3~5-gram TF-IDF cosine은 `0.353981`, 기존 고밀도 train/validation과의 최대값은 `0.382725`이며 상위 쌍은 인접 개념을 서로 다른 교육 목적으로 서술한 정상 쌍이다. 기존 고밀도와 exact concept·text·concept–relation-set 교집합은 모두 0건이다. 수학·논리 표기에 쓰인 특수문자 후보 17건은 모두 의미상 정상이고 control character 및 Unicode escape 파일은 0건이다.

작업 시작 시 고정한 Identity·Attribute·Function train/validation 보호 파일 110개의 SHA-256은 종료 시 110/110 모두 일치했다. 다른 밀도의 데이터는 생성·중복 비교·감사 기준에서 제외했다. 사람용 정본은 `audit_reports/Stage1_(4)_Boundary_Consolidated_Audit.md`, 기계 정본은 `audit_reports/machine/boundary/TinyLM_Stage1_Boundary_Train_v01_v31_Full_Audit_2026-08-31.json`이다.

## 13. Stage1 (4) 개념 경계·반례 validation 설계 원장

### 13.1 목표·schema·분리 해석

```text
설계량: 사용자 지정 약 36K
목표: 600 records = 4 files × 150
train 대비 record 비율: 600/4,650 = 12.90%
파일명: stage1_(4)boundary_high_density_val_v01.json ... v04.json
ID: S1-BNV-0001 ... S1-BNV-0600
type: boundary_packet
split: val
unseen_relation: 모든 record에 boolean으로 포함
일반화 slice: 72/600 = 12.00%, 파일별 18/150
상태: v01~v04 확정·수정 금지
```

Boundary train v01~v31에는 통제 relation 이름 13개가 모두 관측되었다. 따라서 통제 어휘 밖 label을 만들지 않고, `unseen_relation: true`는 **train의 51개 정렬 relation-set에 없던 통제 label 조합**을 사용하는 compositional unseen record로 정의한다. false 528개는 train에서 관측된 정렬 relation-set만 사용하고, true 72개는 train에 없던 정렬 relation-set만 사용한다. true와 false 모두 개별 relation 이름은 train에 이미 등장한 13개 통제 어휘로 제한한다.

Validation 문장은 Boundary train의 exact text, primary concept, `(primary concept, sorted relation-set)`, 5어절 이상 문구를 재사용하지 않는다. train 문장의 단순 바꿔쓰기도 금지하고, 새 전문 맥락에서 겉보기 유사성·인접 범주·상태와 정체성·필요충분·증거 범위·규범 범위의 경계를 판정하게 한다.

### 13.2 4개 예약 concept family

| 버전 | ID 범위 | 새 concept family | 일반화 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 고고학·문화유산·박물관 수집·해석·보존 경계 | 유물/복제품, 출토 맥락/소유 이력, 보존/복원/재현, 연대/시대 판정, 전시/연구/윤리 | 확정 |
| v02 | 0151~0300 | 항공운항·공항·항공교통·비행안전 경계 | 활주로/유도로, 지연/결항, 관제/조종, 고도/고도계, 경보/비상, 승객/수하물 | 확정 |
| v03 | 0301~0450 | 해양항해·선박운항·항만작업·해상안전 경계 | 항로/항적, 정박/계류, 좌초/침몰, 선장/도선사, 조난/긴급, 화물/선용품 | 확정 |
| v04 | 0451~0600 | 심리·인지·행동·상담·심리측정 경계 | 기분/감정, 기억/회상, 주의/의식, 성향/상태, 검사/진단, 상담/치료/윤리 | 확정 |

### 13.3 `other` 편집 분류와 확정 조건

`other`가 필요한 record는 JSON relation 이름을 늘리지 않고 source 원장에서 다음 다섯 편집 유형 중 하나로만 기록한다: `evidence_inference_scope`, `representation_referent_gap`, `normative_authority_scope`, `context_convention_dependence`, `necessary_sufficient_logic`. 이 값은 감사·보고용이며 JSON record의 relation으로 노출하지 않는다.

각 파일은 150개, unseen 18개, ID 범위, 신규 concept, train 분리, 통제 relation, 문장 품질과 전체 감사가 모두 통과한 뒤에만 `확정`으로 바꾼다. 실제 tokenizer가 지정되지 않았으므로 약 36K는 설계 환산량으로 보존하고, 완료 시 문자 수와 `[0-9A-Za-z가-힣]+` 분리 단위를 별도로 보고한다.

### 13.4 2026-08-31 생성·수정·최종 감사 이력

```text
상태: v01~v04 확정·수정 금지
파일/record: 4 files × 150 = 600 records
ID: S1-BNV-0001 ~ S1-BNV-0600
text: 48,932자 / 정규식 분리 단위 11,646개
길이: 최소 66자 / 중앙값 81자 / 평균 81.553자 / 최대 111자
원문: tools/boundary_validation_sources/v01.tsv ... v04.tsv
패키징: tools/build_boundary_validation.py
감사: tools/audit_boundary_validation.py
```

| version | 파일 | ID 범위 | records | unseen | concept family | SHA-256 |
|---|---|---|---:|---:|---|---|
| v01 | `stage1_(4)boundary_high_density_val_v01.json` | 0001~0150 | 150 | 18 | 고고학·문화유산·박물관 수집·해석·보존 경계 | `a61585e24263a191c432300c7bab6566198e2190e92c640b04b4cbe36dc92bda` |
| v02 | `stage1_(4)boundary_high_density_val_v02.json` | 0151~0300 | 150 | 18 | 항공운항·공항·항공교통·비행안전 경계 | `255611dcc98cc08ee8ff3c7389c1876a80837a3121131370064a3471f59ba486` |
| v03 | `stage1_(4)boundary_high_density_val_v03.json` | 0301~0450 | 150 | 18 | 해양항해·선박운항·항만작업·해상안전 경계 | `5fb8a80b9ba996b02ac7890513bebf453dde3219a731f63c4066d0cbc6cc1df0` |
| v04 | `stage1_(4)boundary_high_density_val_v04.json` | 0451~0600 | 150 | 18 | 심리·인지·행동·상담·심리측정 경계 | `a7e308c35389e4487e2bbc476d92f5009a611b51d331ff1f5d69ad3717e6430a` |

Relations 전체 분포는 다음과 같다.

| relation | 횟수 | relation | 횟수 |
|---|---:|---|---:|
| `is_a` | 0 | `subclass_of` | 0 |
| `part_of` | 39 | `classification` | 186 |
| `boundary` | 600 | `contrast` | 173 |
| `comparison` | 47 | `function` | 121 |
| `role` | 61 | `process` | 140 |
| `state` | 308 | `attribute` | 66 |
| `other` | 131 |  |  |

`other` 131건의 편집상 상위 5유형은 증거·추론 범위 63건, 규범·권한 범위 41건, 표현–지시대상 간극 11건, 문맥·관례 의존 10건, 필요·충분 논리 6건이다. 대표 concept는 각각 `작가서명과진위증명`, `소장기록과소유권`, `색맞춤과원색복원`, `분류명과실제용도`, `양식유사성과동시대성`이다.

일반화 slice는 `unseen_relation: true` 72건과 false 528건으로 전체 12.00%이며 각 파일은 true 18건, false 132건이다. true에서 사용한 12개 고유 정렬 relation-set은 모두 Boundary train의 51개 set에 없고, false의 모든 set은 train에 관측되었다. 개별 relation 이름은 true/false 전부 train에서 관측된 13개 통제 어휘만 사용했으며 train 미관측 개별 label은 0건이다.

1차 통합 감사에서 내부 반복 5어절 6개, Boundary train 공통 5어절 2개, 기존 다른 고밀도 train과 겹친 primary concept 4개를 발견해 validation source만 직접 고쳤다. 이어 교차 유사도 상위 문장을 사람이 대조하여 train 교육 객체와 실질적으로 겹친 `조류/해류`, `무작위배정/표집`, `상관/인과`, 인접한 `맹검/기만` 문항을 각각 `조석류/취송류`, `개별/군집 무작위화`, `기제설명/통계예측`, `조건은폐/불완전고지` 판정으로 다시 설계했다.

최종 통합 감사 결과 JSON·UTF-8·metadata·schema·ID·source↔JSON·통제 relation·unseen 선언 오류는 모두 0건이다. 내부 exact ID·primary concept·text·concept–relation-set 중복, 반복 5어절, 반복 4어절 도입부도 모두 0건이다. Boundary train 및 기존 고밀도 전체와 exact primary concept·text·concept–relation-set·5어절 교집합은 모두 0건이다. 내부 최대 문자 3~5-gram TF-IDF cosine은 `0.265277`, Boundary train 교차 최대는 `0.207517`, 기존 고밀도 전체 교차 최대는 `0.212943`이다. 상위 pair를 문장까지 직접 검토했으며 서로 다른 판정 축 또는 전문 영역의 정상적인 인접 개념이었다.

Primary concept 직후 조사 오류는 0건이다. 문장 전체의 기계 조사 후보 5건은 `전문가`의 어휘 말음과 `붙잡는`, `넘겨받는`, `보고받는`, `평가받는`의 활용 어미를 조사로 오인한 false positive로 확인되어 실제 오류는 0건이다. control character, Unicode escape, 비정상 문자 후보도 0건이다.

작업 시작 시 고정한 Identity·Attribute·Function train/validation, Stage2 Attribute 확정 파일, Boundary train 보호 파일 141개의 SHA-256은 종료 시 141/141 모두 일치했다. 다른 밀도와 held-out은 생성·중복 비교·감사 기준에서 제외했다. 사람용 정본은 `audit_reports/Stage1_(4)_Boundary_Consolidated_Audit.md`, 기계 정본은 `audit_reports/machine/boundary/TinyLM_Stage1_Boundary_Validation_v01_v04_Audit_2026-08-31.json`이다.

## 14. Stage1 (5)~(10) train 공통 등록

사용자 지정 train 총량은 14,550 records, 97 files, 설계 환산 1,260K다. 각 파일은 정확히 150 records이며 아래 예약 family 하나만 담당한다. Stage1 (5)~(10) validation은 2026-09-01에 별도로 승인되었고 §21~§27의 신규 family와 ID를 따른다.

| 영역 | slug / type | ID prefix | 목표 | 설계량 | 영역 관계 규약 |
|---|---|---|---:|---:|---|
| (5) 부분–전체 | `partwhole` / `partwhole_packet` | `S1-PWH-` | 3,450 = 23×150 | 300K | 모든 record에 `part_of` 필수 |
| (6) 상태·상태 변화 | `statechange` / `statechange_packet` | `S1-SCH-` | 3,450 = 23×150 | 300K | 모든 record에 `state`, `process` 필수; 전후 상태와 전이 조건 명시 |
| (7) 공간 관계 | `spatial` / `spatial_packet` | `S1-SPH-` | 2,400 = 16×150 | 210K | 전용 통제 label이 없으므로 모든 record에 `other` 필수; `part_of`는 실제 부분 관계에만 사용 |
| (8) 비교·대조 | `comparison` / `comparison_packet` | `S1-COH-` | 2,100 = 14×150 | 180K | 모든 record에 `comparison` 또는 `contrast` 중 하나 이상 필수 |
| (9) 문맥 통합 | `context` / `context_packet` | `S1-CTH-` | 1,800 = 12×150 | 150K | 3~6개 명시 concept, 3~5개 의미 일치 relation, 단일 필수 label은 강제하지 않음 |
| (10) 타입·부정·불확실성 | `type_uncertainty` / `type_uncertainty_packet` | `S1-TUH-` | 1,350 = 9×150 | 120K | 모든 record에 `other`와 `classification`·`boundary`·`state` 중 하나 이상 필수 |

파일명은 `stage1_(N)<slug>_high_density_train_vNN.json` 형식을 쓴다. ID는 각 영역에서 `0001`부터 독립적으로 연속 증가한다. train record에는 `unseen_relation`을 넣지 않는다. 모든 relation은 13개 통제 어휘 안에서 2~5개를 중복 없이 쓰며, text에 실제로 드러난 의미만 label로 부여한다.

### 14.1 공간·타입 영역의 `other` 해석

공간의 안/밖·위/아래·좌/우·접촉·거리·방향·좌표는 기존 12개 이름 중 정확히 맞는 relation이 없으므로 R2에 따라 `other`를 사용한다. source 편집 원장에서는 JSON relation을 늘리지 않고 `containment_location`, `directional_order`, `adjacency_connectivity`, `distance_proximity`, `reference_frame_projection` 다섯 유형으로만 분류한다.

타입·부정·불확실성의 명제 부정, 부재, 미관측, 가능성, 메타타입도 전용 relation 이름을 만들지 않고 `other`로 보수적으로 기록한다. source 편집 유형은 `metatype_reference`, `negation_scope`, `absence_nonexistence`, `unknown_unobserved`, `uncertainty_evidence` 다섯 가지다. 이 편집 유형은 감사·보고용이며 JSON relation 값이 아니다.

### 14.2 생성·확정 순서

영역 순서는 (5)→(6)→(7)→(8)→(9)→(10), 각 영역 안에서는 v01부터 오름차순이다. 한 source 150개를 직접 작성하고 JSON 포장·전수 감사를 통과한 뒤에만 해당 row를 `확정`으로 바꾼다. 중단되면 실제 source 행 수, JSON, 감사 결과를 대조하고 마지막 `확정` 다음 row부터 재개한다. 예약 row의 family 이름과 축은 context 압축 뒤에도 바꾸거나 재사용하지 않는다.

## 15. Stage1 (5) 부분–전체 train 설계 원장

```text
목표: 3,450 records = 23 files × 150 / 약 300K
파일: stage1_(5)partwhole_high_density_train_v01.json ... v23.json
ID: S1-PWH-0001 ... S1-PWH-3450
type/split: partwhole_packet / train
핵심 오류 억제: 부분→전체 속성의 무조건 상속, 구성요소와 소유물·내용물·구성원의 혼동, 전체와 부분의 방향 반전
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 인체 기관계·기관·조직·세포의 구성 계층 | 기관계/기관, 기관/조직, 조직/세포, 좌우 쌍, 층·막·관 구조 | 확정 |
| v02 | 0151~0300 | 식물 뿌리·줄기·잎·꽃·열매·종자의 구성 | 기관/조직, 꽃 기관, 열매/씨, 관다발, 생장점 | 확정 |
| v03 | 0301~0450 | 동물 골격·근육·외피·감각기관의 구성 | 뼈/골격, 근육군, 체절, 껍질·깃·비늘, 감각 구조 | 확정 |
| v04 | 0451~0600 | 세포 소기관·막계·분자복합체의 구성 | 핵·막·소기관, 세포골격, 리보솜, 단백질 복합체, 분자 하위단위 | 확정 |
| v05 | 0601~0750 | 생태계·먹이망·서식지·물질순환의 구성 | 개체군/군집, 영양 단계, 서식지 모자이크, 탄소·질소 저장고 | 확정 |
| v06 | 0751~0900 | 지층·암석·토양단면·유역·하천망의 구성 | 광물/암석, 지층/층서, 토양층위, 지류/본류, 소유역/유역 | 확정 |
| v07 | 0901~1050 | 은하·항성계·행성계·천체 내부의 구성 | 은하 구조, 항성계, 행성/위성, 대기층, 핵·맨틀·지각 | 확정 |
| v08 | 1051~1200 | 건축 구조·외피·실내·설비의 구성 | 기초/골조, 벽·지붕 외피, 방·동선, 전기·급배수·환기 설비 | 확정 |
| v09 | 1201~1350 | 도로·교량·터널·상하수도 도시망의 구성 | 차로/도로, 교량 경간, 터널 단면, 관망, 맨홀·밸브·배수구 | 확정 |
| v10 | 1351~1500 | 자동차·철도차량·자전거의 조립 계층 | 차체/섀시, 동력계, 제동·조향, 대차, 차륜·구동 부품 | 확정 |
| v11 | 1501~1650 | 항공기·헬리콥터·우주선의 조립 계층 | 동체/날개, 회전익, 추진·조종면, 항공전자, 탑재체·단계 | 확정 |
| v12 | 1651~1800 | 선박·해양플랜트·항만설비의 구성 | 선체 구획, 갑판·기관, 계류계, 하역장치, 방파제·선석 | 확정 |
| v13 | 1801~1950 | 기계요소·동력전달·생산라인의 구성 | 축·기어·베어링, 링크, 유압회로, 공정 셀, 라인 모듈 | 확정 |
| v14 | 1951~2100 | 전기회로·전자기기·전력설비의 구성 | 소자/회로, 기판/모듈, 전원부, 배선·접지, 변전·보호 계통 | 확정 |
| v15 | 2101~2250 | 컴퓨터 하드웨어·저장장치·네트워크의 구성 | CPU 하위부, 메모리 계층, 디스크 블록, 포트·링크·노드 | 확정 |
| v16 | 2251~2400 | 소프트웨어·코드·데이터·문서의 논리 구성 | 패키지/모듈, 함수/문장, 객체/필드, 표/행·열, 문서/절·문단 | 확정 |
| v17 | 2401~2550 | 담화·문장·구·단어·형태소의 언어 구성 | 담화 단위, 문장 성분, 구·절, 합성어, 어근·접사 | 확정 |
| v18 | 2551~2700 | 집합·식·증명·도형의 수학적 구성 | 집합/원소, 식/항, 행렬/성분, 증명/보조정리, 도형/면·변·꼭짓점 | 확정 |
| v19 | 2701~2850 | 지도·지형구역·행정구역·필지의 공간 계층 | 도엽, 지형 단위, 국가/지방, 구역/필지, 경계·내부 단위 | 확정 |
| v20 | 2851~3000 | 조직·부서·팀·위원회·프로젝트의 구성 | 조직 단위, 직위와 구성원, 위원회, 작업반, 프로젝트 작업분해 | 확정 |
| v21 | 3001~3150 | 법령·계약·사건기록·증거 묶음의 문서 구성 | 장·절·조·항, 계약 조항, 사건기록, 첨부, 증거목록 | 확정 |
| v22 | 3151~3300 | 회화·조각·음악·공연·영상 작품의 구성 | 화면 요소, 조각 부재, 악장·구절, 장면·막, 숏·트랙 | 확정 |
| v23 | 3301~3450 | 식재료·조리법·한 끼·포장·생산묶음의 구성 | 재료/요리, 단계/조리법, 메뉴/식사, 용기/포장, 로트/단위품 | 확정 |

### 15.1 2026-08-31 v01~v23 생성·최종 감사 이력

```text
상태: v01~v23 완료·감사 통과·수정 금지
파일/record: 23 files × 150 = 3,450 records
ID: S1-PWH-0001 ~ S1-PWH-3450
concept family: v01 인체 구성 계층 / v02 식물 기관·조직·생식구조 구성 / v03 동물 골격·근육·외피·감각기관 구성 / v04 세포 소기관·막계·분자복합체 구성 / v05 생태계·먹이망·서식지·물질순환 구성 / v06 지층·암석·토양·유역·하천망 구성 / v07 은하·항성계·행성계·천체 내부 구성 / v08 건축 구조·외피·실내·설비 구성 / v09 도로·교량·터널·상하수도 도시망 구성 / v10 자동차·철도차량·자전거 조립 계층 / v11 항공기·헬리콥터·우주선 조립 계층 / v12 선박·해양플랜트·항만설비 구성 / v13 기계요소·동력전달·생산라인 구성 / v14 전기회로·전자기기·전력설비 구성 / v15 컴퓨터 하드웨어·저장장치·네트워크 구성 / v16 소프트웨어·코드·데이터·문서 논리 구성 / v17 담화·문장·구·단어·형태소 언어 구성 / v18 집합·식·증명·도형 수학 구성 / v19 지도·지형구역·행정구역·필지 공간 계층 / v20 조직·부서·팀·위원회·프로젝트 구성 / v21 법령·계약·사건기록·증거 문서 구성 / v22 회화·조각·음악·공연·영상 작품 구성 / v23 식재료·조리법·한 끼·포장·생산묶음 구성
text: 309,841자 / 정규식 분리 단위 67,889개
길이: 최소 75자 / 중앙값 90자 / 평균 89.809자 / 최대 130자
Stage1 (5) 잔여: 0 records = 0 files
Stage1 (5)~(10) 전체 잔여: 11,100 records = 74 files
v01 JSON SHA-256: BA06BCC5660CBF9BF297741EC923D2B08B5FCFC5E1A92098DCA0C6AEC22C265A
v02 JSON SHA-256: D3F104D88CE9E937678298304FA72D6C30DC2F14EFBF8EE58C3E2F5E9F1AD4D5
v03 JSON SHA-256: B23E0CD731BD1705DBDB20116AFE847A365C207408B7752B45E4A6CCEBFDF8C0
v04 JSON SHA-256: 4A300DA1D3A98908D3C7755A099B0441F7FF9587ACAEABBB5734DFEC8CD25763
v05 JSON SHA-256: 81E61680850661343C0E3516804571CB5241F295F7E248CB96FEB348EF7A2975
v06 JSON SHA-256: 6E0237695758F93DDB16DD4A3F37C684ACAFD0C9C322857293B6003FE04E3614
v07 JSON SHA-256: 0BA6A9608D6CA99D17F9B426D6371D82943755E21FE33CC665FC210D364E7485
v08 JSON SHA-256: AA92D45F7613759751414F1B830C24D1BD37FE725CE5F723299B3BB44422867E
v09 JSON SHA-256: 872387810213933B90A83E9DDA921B015BC651E813B8CDE5917CE42839D8A539
v10 JSON SHA-256: 6D0C193216FF6E13940FAA9AAF6A85FA4903AB71DF75DA2B374C03AEC5FF9031
v11 JSON SHA-256: ED1057DC86D934794151460C1E138ED88E4A07D7B9BFF80AD0791529B9754A88
v12 JSON SHA-256: 6BAB91828A513ACCC000CD346CB16D19A637B30418CE17454ED3ABE7BC50818A
v13 JSON SHA-256: C702240D2D7D7A1AAD025F77C77D7AB5FDA371210C5194A195ECA4CDB9BC64C5
v14 JSON SHA-256: 3E0B71BDED77894A2C78D6BD5418BEDF0FBB36E537A739A54074B8657B77BC39
v15 JSON SHA-256: 5B5622011C6A7198FABEF385729D1BEB0437676BFC3235321AA0C619FC236D74
v16 JSON SHA-256: EE2193034CDCBB355D98B0BDC5466E79C3672985C8663AC8E80F8A1CBFFFF844
v17 JSON SHA-256: E9C92133AAC8DFA2DF8CEA3C1F536E23C7B3B5441D6CB149179D35F3AE337EE5
v18 JSON SHA-256: 0477813010795136D6274905687CE4B0291C4BB065A3F576449650A0FF490529
v19 JSON SHA-256: 19B82DE0A4C5F67FCF926E14EEF63AEB092D239F61DB40A129874E9DFF0CA8BD
v20 JSON SHA-256: 01C70946CEC4608AA8F110DC18CEB1F26347904FF37733E6C973199E59E0E937
v21 JSON SHA-256: CB551CE4FDEDB577CA1E2D82428681F8B513EBB68B2F78FB1B708B7A0FF8D950
v22 JSON SHA-256: C9860444C1D8F8316C0F2359C9AD5C6E0F250CBF5508393FD09B97C463D62966
v23 JSON SHA-256: 0E3E6ACD45F31792E8F6BB5B61D54D2BB60EEF82A8D89F9B0FD44243600C199C
```

Relations 누적은 `is_a` 21, `subclass_of` 30, `part_of` 3,450, `classification` 1,149, `boundary` 766, `contrast` 218, `comparison` 85, `function` 2,175, `role` 275, `process` 907, `state` 571, `attribute` 286, `other` 407이다. v23 단독은 각각 0, 0, 150, 49, 21, 4, 5, 56, 7, 73, 50, 26, 9이다. 실제 의미가 없는 상하위·비교 label은 분포 채우기 목적으로 추가하지 않았다.

`other` 누적 편집 유형 상위 5개는 추상 구획·과정 구조 166, 집합 정체성 135, 물질적 몫 46, 구성원·구조부품 경계 34, 공통 발생 기원 묶음 26이다. 이 유형명은 source 감사용이고 JSON에는 통제 relation `other`만 기록한다.

최종 통합 재감사에서 JSON·UTF-8·schema·metadata·ID·source 대응·relations 오류는 모두 0건이다. exact ID/concept/text/concept–relation-set 중복은 내부 및 현 시점 기존 고밀도 32,800 records와의 교차 비교에서 모두 0건이고, 내부·교차 반복 5어절과 반복 4어절 도입부도 0건이다. primary concept 직후 조사 오류와 실제 광역 조사 오류는 0건이다. 광역 조사 후보 33건은 모두 실제 조사 오류가 아닌 어휘 말음 오탐이다. 내부 최대 문자 3~5-gram TF-IDF cosine은 `0.342280`, 기존 고밀도 대비 최대는 `0.324924`다. v23 source는 다섯 하위축 각 30행, 최소 82자를 만족했고 초안의 비통제 relation 2건을 `other`로 교정한 뒤 첫 실제 누적 감사에서 모든 항목을 통과했다.

상세 결과는 `audit_reports/machine/TinyLM_Stage1_PartWhole_Train_v01_v23_Final_Audit_2026-08-31.json`과 `audit_reports/Stage1_(5)_PartWhole_Consolidated_Audit.md`에 보존한다. 전체 생성 시작 시 고정한 기존 정본 146개는 v23 확정 직후 146/146 SHA-256이 일치했고, 빌더는 Part–Whole v01~v22의 source 재구성 기대 bytes와 기존 JSON 일치를 확인한 뒤 v23만 기록했다. v01~v23은 이 절과 §9의 정본이며 Stage1 (5)는 완료됐다.

## 16. Stage1 (6) 상태·상태 변화 train 설계 원장

```text
목표: 3,450 records = 23 files × 150 / 약 300K
파일: stage1_(6)statechange_high_density_train_v01.json ... v23.json
ID: S1-SCH-0001 ... S1-SCH-3450
type/split: statechange_packet / train
핵심 오류 억제: 대상과 상태의 동일시, 한 시점 관찰을 영구 속성으로 일반화, 전이 조건·가역성·중간 상태 누락
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 물질 상·용해·결정화·응고·기화 상태 전이 | 고체/액체/기체, 용해/석출, 결정/비정질, 상평형, 과냉각 | 확정 |
| v02 | 0151~0300 | 온도·열평형·가열·냉각·열저장 상태 변화 | 승온/강온, 열평형, 과열, 축열·방열, 단열 뒤 완화 | 확정 |
| v03 | 0301~0450 | 화학 반응·농도·산염기·산화환원 상태 변화 | 반응 진행, 농도, pH, 산화수, 평형 이동, 촉매 전후 | 확정 |
| v04 | 0451~0600 | 운동·정지·진동·변형·파손·마모 상태 변화 | 속도 상태, 진동 모드, 탄성/소성, 균열, 피로·마모 | 확정 |
| v05 | 0601~0750 | 전기회로 전원·충전·스위칭·고장·복구 상태 | 통전/차단, 충방전, 논리 상태, 과부하, 보호 동작·복귀 | 확정 |
| v06 | 0751~0900 | 운영체제 프로세스·작업·자원 잠금 생명주기 | 생성/준비/실행/대기/종료, 중단, 교착, 재시작 | 확정 |
| v07 | 0901~1050 | 데이터·문서·버전·승인·보관 생명주기 | 초안/검토/승인, 유효/폐기, 버전 분기, 보관·복원 | 확정 |
| v08 | 1051~1200 | 네트워크 연결·세션·동기화·장애 상태 전이 | 탐색/연결/인증, 정상/저하/단절, 재전송, 재동기화 | 확정 |
| v09 | 1201~1350 | 기기 전원모드·배터리·충전·열제한 상태 변화 | 켜짐/대기/절전, 충전 단계, 잔량, 과열 제한, 정상 복귀 | 확정 |
| v10 | 1351~1500 | 건물 점유·출입·방재·보안 운용 상태 변화 | 개방/폐쇄, 점유, 경계, 화재모드, 대피, 시설 복구 | 확정 |
| v11 | 1501~1650 | 차량·열차·항공기·선박 운항 단계와 상태 전이 | 준비/출발/순항/정차, 지연, 우회, 비상, 운항 종료 | 확정 |
| v12 | 1651~1800 | 주문·포장·운송·인도·반품 물류 상태 변화 | 접수/할당, 포장, 출고, 이동, 인도 실패, 반품·회수 | 확정 |
| v13 | 1801~1950 | 제조 공정품·설비·품질 판정 상태 변화 | 원재료/재공/완성, 가동/정지, 검사대기, 합격/보류/재작업 | 확정 |
| v14 | 1951~2100 | 식품 조리·발효·숙성·저장·변질 상태 변화 | 익힘, 유화, 발효 단계, 숙성, 냉각, 산패·부패 경계 | 확정 |
| v15 | 2101~2250 | 식물 발아·생장·개화·결실·휴면·스트레스 변화 | 종자 상태, 영양생장, 생식전환, 낙엽, 휴면, 회복 | 확정 |
| v16 | 2251~2400 | 동물 활동·섭식·이동·번식·휴식 행동 상태 | 경계/탐색, 섭식, 이동, 둥지, 번식 단계, 휴식 전환 | 확정 |
| v17 | 2401~2550 | 사람 수면·각성·운동·피로·회복의 일반 생리 상태 | 수면 단계, 각성, 운동 강도, 피로 누적, 휴식·회복 | 확정 |
| v18 | 2551~2700 | 대기·구름·전선·강수·폭풍의 발달과 소멸 | 기단 변화, 구름 발달, 전선 통과, 강수 전환, 폭풍 약화 | 확정 |
| v19 | 2701~2850 | 하천·호수·지하수·홍수·가뭄 수문 상태 변화 | 수위·유량, 저수, 침투, 범람, 갈수, 회복 | 확정 |
| v20 | 2851~3000 | 풍화·침식·퇴적·사면·지각변형 상태 변화 | 풍화 단계, 운반/퇴적, 사면 안정, 단층 운동, 지형 재편 | 확정 |
| v21 | 3001~3150 | 회의·협업·프로젝트·결정·갈등 상태 변화 | 제안/논의/합의, 작업 진행, 보류, 충돌, 조정·종료 | 확정 |
| v22 | 3151~3300 | 계좌·거래·청구·계약·심사 상태 생명주기 | 개설/활성/정지, 승인/거절, 결제, 연체, 해지·복구 | 확정 |
| v23 | 3301~3450 | 학습·주의·기억·정서·과제진행 상태 변화 | 준비/집중/전환, 습득/망각, 확신, 정서 조절, 완료·재시도 | 확정 |

### 16.1 Stage1 (6) train 확정 기록 — 2026-09-01

- 23파일, 3,450레코드, `S1-SCH-0001`~`S1-SCH-3450`을 생성·확정했다.
- 관계 분포: `is_a` 0, `subclass_of` 0, `part_of` 13, `classification` 454, `boundary` 820, `contrast` 467, `comparison` 92, `function` 827, `role` 206, `process` 3,450, `state` 3,450, `attribute` 374, `other` 198.
- `other` 유형 분포: 잠재·관측 상태 121, 전이 촉발 조건 44, 생명주기 상태 25, 회복·저하 5, 가역 범위 3.
- 최종 감사: JSON/스키마/메타데이터/통제어휘/ID/원본-JSON 대응 오류 0, 정확 개념·문장 중복 0, 내부·교차 5어절 반복 0, 반복 시작구 0, 개념 조사 오류 0.
- 유사도 상한 관측: 내부 0.356120, 기존 고밀도 교차 0.299638. 광범위 조사 후보 44건은 문맥상 정상인 일반어 탐지 오탐이다.
- 정본 감사 파일: `audit_reports/machine/TinyLM_Stage1_StateChange_Train_v01_v23_Final_Audit_2026-09-01.json`, 통합 보고서 `audit_reports/Stage1_(6)_StateChange_Consolidated_Audit.md`.
- 이 절의 v01~v23 JSON과 대응 TSV는 확정 보호 대상으로 취급하며 후속 영역 생성 중 수정하지 않는다.

## 17. Stage1 (7) 공간 관계 train 설계 원장

```text
목표: 2,400 records = 16 files × 150 / 약 210K
파일: stage1_(7)spatial_high_density_train_v01.json ... v16.json
ID: S1-SPH-0001 ... S1-SPH-2400
type/split: spatial_packet / train
핵심 오류 억제: 안에 있음과 부분임의 혼동, 관찰자 기준 좌우와 대상 기준 좌우의 혼동, 접촉·인접·연결·거리의 과잉 동일시
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 가정 실내 물체·가구·용기의 배치 관계 | 안/밖, 위/아래, 표면, 사이, 모서리, 겹침·접촉 | 확정 |
| v02 | 0151~0300 | 건물 층·방·복도·계단·출입구의 공간 위상 | 층간, 방 연결, 복도 분기, 출입 경계, 수직 동선 | 확정 |
| v03 | 0301~0450 | 도시 블록·도로·교차로·공원·시설의 배치 | 블록 내부, 맞은편, 교차, 인접 필지, 중심/외곽 | 확정 |
| v04 | 0451~0600 | 도로 차량·차로·교차로·진출입의 상대 위치 | 선행/후행, 좌우 차로, 합류, 교차점 전후, 안전 간격 | 확정 |
| v05 | 0601~0750 | 철도역·승강장·선로·분기기·차량의 배치 | 상하행 기준, 플랫폼 면, 선로 사이, 분기, 정차 위치 | 확정 |
| v06 | 0751~0900 | 공항 활주로·유도로·계류장·게이트 공간 관계 | 평행/교차, 대기 위치, 보호구역, 게이트 인접, 이동 경로 | 확정 |
| v07 | 0901~1050 | 항만·선박·선석·항로·정박지 공간 관계 | 접안면, 선수/선미 기준, 항로 안팎, 정박 간격, 수역 경계 | 확정 |
| v08 | 1051~1200 | 산지·하천·유역·해안·섬의 지리 공간 관계 | 상류/하류, 능선/계곡, 내륙/연안, 포위·연결, 인접 수역 | 확정 |
| v09 | 1201~1350 | 지도 좌표·축척·방위·투영·기준계 관계 | 좌표축, 절대/상대 위치, 축척 거리, 방위, 투영 왜곡 | 확정 |
| v10 | 1351~1500 | 천구·궤도·행성·위성·관측자의 상대 위치 | 전경/배경, 합·충, 공전면, 가림, 관측자 기준 방향 | 확정 |
| v11 | 1501~1650 | 인체 자세·해부 방향·기관의 상대 위치 | 앞/뒤, 안쪽/가쪽, 몸쪽/먼쪽, 표면/깊이, 좌우 기준 | 확정 |
| v12 | 1651~1800 | 생물 서식지·둥지·영역·군집의 미소공간 | 영역 내부, 경계, 층상 분포, 군집 간격, 은신처 접근 | 확정 |
| v13 | 1801~1950 | 분자·결정·세포·조직의 미시 공간 배열 | 결합 위치, 격자 이웃, 막 안팎, 극성 방향, 층·구획 | 확정 |
| v14 | 1951~2100 | 공장 작업셀·생산선·창고·적치의 공간 배치 | 공정 순서 위치, 통로, 적치 높이, 구역, 장비 간격 | 확정 |
| v15 | 2101~2250 | 메모리 주소·파일 경로·네트워크 위상의 논리 공간 | 주소 범위, 상위/하위 경로, 인접 블록, 링크, 논리 거리 | 확정 |
| v16 | 2251~2400 | 화면·페이지·도표·영상 레이어의 시각 배치 | 정렬, 여백, 전후 레이어, 캡션 위치, 좌표·자르기 | 확정 |

### 17.1 Stage1 (7) train 확정 기록 — 2026-09-01

- 16파일, 2,400레코드, `S1-SPH-0001`~`S1-SPH-2400`을 생성·확정했다.
- 관계 분포: `is_a` 0, `subclass_of` 0, `part_of` 169, `classification` 532, `boundary` 1,183, `contrast` 147, `comparison` 294, `function` 618, `role` 234, `process` 475, `state` 697, `attribute` 451, `other` 2,400.
- `other` 유형 분포: 포함·위치 480, 방향·순서 480, 인접·연결 480, 거리·근접 480, 기준계·투영 480.
- 최종 감사: JSON/스키마/메타데이터/통제어휘/ID/source 대응 오류 0, 정확 개념·문장·개념-relation-set 중복 0, 내부·교차 5어절 반복 0, 반복 시작구 0, 개념 조사 오류 0.
- 문자 3~5-gram TF-IDF cosine 상한은 내부 0.348472, 기존 고밀도 교차 0.220711이다.
- 정본 감사 파일: `audit_reports/machine/TinyLM_Stage1_Spatial_Train_v01_v16_Final_Audit_2026-09-01.json`, 통합 보고서 `audit_reports/Stage1_(7)_Spatial_Consolidated_Audit.md`.
- 이 절의 v01~v16 JSON과 대응 TSV는 확정 보호 대상으로 취급하며 후속 영역 생성 중 수정하지 않는다.

## 18. Stage1 (8) 비교·대조 train 설계 원장

```text
목표: 2,100 records = 14 files × 150 / 약 180K
파일: stage1_(8)comparison_high_density_train_v01.json ... v14.json
ID: S1-COH-0001 ... S1-COH-2100
type/split: comparison_packet / train
핵심 오류 억제: 비교 기준 누락, 단위·모집단·시점이 다른 값의 직접 비교, 한 축의 우위를 전체 우위로 확대
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 길이·면적·부피·질량·밀도의 기준화 비교 | 단위 변환, 절대/상대 차이, 형상 효과, 질량/밀도 분리 | 확정 |
| v02 | 0151~0300 | 시각·기간·속도·빈도·지연의 시간 비교 | 시작점, 경과시간, 평균/순간 속도, 주기, 지연 분포 | 확정 |
| v03 | 0301~0450 | 온도·열량·에너지·동력·효율의 비교 | 상태량/이동량, 에너지/동력, 입력/출력, 효율 기준 | 확정 |
| v04 | 0451~0600 | 재료 강도·강성·연성·인성·내구성의 비교 | 시험 조건, 방향성, 파손 모드, 초기 성능/수명 | 확정 |
| v05 | 0601~0750 | 생물 형태·성장·대사·생리 지표의 비교 | 체격 보정, 성장 단계, 종내/종간, 환경 조건 | 확정 |
| v06 | 0751~0900 | 생태 개체수·밀도·다양성·생산성의 비교 | 조사 면적, 표본 노력, 풍부도/균등도, 계절·서식지 | 확정 |
| v07 | 0901~1050 | 통계 분포·중심·산포·비율·위험의 비교 | 평균/중앙값, 분산, 기저율, 효과크기, 불확실성 | 확정 |
| v08 | 1051~1200 | 측정법·센서·검사의 정확도·정밀도 비교 | 기준값, 반복성, 민감도/특이도, 검출한계, 교정 | 확정 |
| v09 | 1201~1350 | 알고리즘·시스템의 시간·메모리·확장성 비교 | 입력 크기, 처리량, 지연, 메모리, 최악/평균 조건 | 확정 |
| v10 | 1351~1500 | 제품·도구의 기능·사용성·비용·유지보수 비교 | 과업 적합성, 사용자 조건, 총비용, 수리·교체 | 확정 |
| v11 | 1501~1650 | 교통수단의 속도·용량·안전·에너지 비교 | 노선·거리, 탑승률, 사고 노출, 단위수송 에너지 | 확정 |
| v12 | 1651~1800 | 언어·문서의 명료성·격식·응집성·정보밀도 대조 | 독자, 목적, 어휘·문장, 근거 구조, 요약 손실 | 확정 |
| v13 | 1801~1950 | 정책·서비스의 도달률·효과·형평·비용 대조 | 대상 집단, 기준선, 결과 지표, 분배 효과, 기간 | 확정 |
| v14 | 1951~2100 | 의사결정 대안의 효용·위험·가역성·제약 비교 | 다기준, trade-off, 최악 결과, 되돌림 비용, 자원 제약 | 확정 |

### 18.1 Stage1 (8) train 확정 기록 — 2026-09-01

- 14파일, 2,100레코드, `S1-COH-0001`~`S1-COH-2100`을 생성·확정했다.
- 관계 분포: `is_a` 0, `subclass_of` 0, `part_of` 4, `classification` 198, `boundary` 354, `contrast` 449, `comparison` 1,701, `function` 303, `role` 60, `process` 270, `state` 452, `attribute` 409, `other` 2,100.
- `other` 유형 분포: 다차원 순위, 질적 대조, 기준 정규화, 상황 의존 순위, 불확실성 구간이 각각 420.
- 텍스트: 168,771자 / 정규식 분리 단위 39,297개. 길이는 최소 63자, 중앙값 80자, 평균 80.367자, 최대 107자다.
- 최종 감사: JSON/스키마/메타데이터/통제어휘/ID/source 대응 오류 0, 정확 개념·문장·개념-relation-set 중복 0, 내부·교차 5어절 반복 0, 반복 시작구 0, 개념 조사 오류 0.
- 문자 3~5-gram TF-IDF cosine 상한은 내부 0.324903, 기존 고밀도 교차 0.418577이다.
- 정본 감사 파일: `audit_reports/machine/TinyLM_Stage1_Comparison_Train_v01_v14_Final_Audit_2026-09-01.json`, 통합 보고서 `audit_reports/Stage1_(8)_Comparison_Consolidated_Audit.md`.
- 이 절의 v01~v14 JSON과 대응 TSV는 확정 보호 대상으로 취급하며 후속 영역 생성 중 수정하지 않는다.

## 19. Stage1 (9) 문맥 통합 train 설계 원장

```text
목표: 1,800 records = 12 files × 150 / 약 150K
파일: stage1_(9)context_high_density_train_v01.json ... v12.json
ID: S1-CTH-0001 ... S1-CTH-1800
type/split: context_packet / train
핵심 능력: 사람·대상·위치·도구·행동·상태·시간을 한 상황에서 동시에 유지하고 지시 대상과 결과를 연결
```

각 record의 `concepts`는 primary 상황 concept 뒤에 문장에 실제 등장하는 핵심 객체 2~5개를 더해 총 3~6개다. 같은 객체를 다른 표기로 중복하지 않으며, 대명사·생략이 있더라도 선행 대상을 문장 안에서 복원할 수 있어야 한다.

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 가정의 준비·정리·세탁·수리 일상 상황 | 사람, 방, 물건, 도구, 순서, 완료·미완료 상태 | 확정 |
| v02 | 0151~0300 | 주방의 재료 준비·조리·보관·제공 상황 | 재료, 기구, 온도, 시간, 용기, 조리 상태 | 확정 |
| v03 | 0301~0450 | 교실의 설명·질문·과제·피드백·평가 상황 | 교사/학습자, 자료, 문제, 답, 피드백, 진행 상태 | 확정 |
| v04 | 0451~0600 | 진료·예약·검사·결과 안내·추적관리 상황 | 이용자, 의료진, 일정, 검사, 기록, 다음 조치 | 확정 |
| v05 | 0601~0750 | 작업장의 주문·재료·기계·검사·재작업 상황 | 작업자, 설비, 공정품, 작업지시, 측정, 품질 상태 | 확정 |
| v06 | 0751~0900 | 상점의 재고·주문·결제·교환·고객응대 상황 | 고객/직원, 상품, 재고, 영수증, 결제, 처리 상태 | 확정 |
| v07 | 0901~1050 | 창고·배송의 입고·분류·상차·이동·인도 상황 | 화물, 위치, 작업자, 차량, 수취인, 추적 상태 | 확정 |
| v08 | 1051~1200 | 대중교통의 승차·환승·지연·우회·도착 상황 | 승객, 노선, 정류장, 시간, 연결편, 운행 상태 | 확정 |
| v09 | 1201~1350 | 건물 경보·대피·신고·구조·복구 상황 | 경보, 점유자, 출구, 담당자, 위험 구역, 복구 상태 | 확정 |
| v10 | 1351~1500 | 환경 현장조사의 지점·센서·시료·기상·기록 상황 | 조사자, 위치, 장비, 시료, 조건, 측정 기록 | 확정 |
| v11 | 1501~1650 | 협업 소프트웨어의 이슈·변경·검토·시험·배포 상황 | 사용자/개발자, 이슈, 분기, 변경, 테스트, 릴리스 | 확정 |
| v12 | 1651~1800 | 공공행정의 신청·서류·심사·보완·결정 상황 | 신청인, 담당자, 양식, 증빙, 기한, 처리 결과 | 확정 |

### 19.1 생성·감사 확정 기록 (2026-09-01)

- 산출물: `stage1_(9)context_high_density_train_v01.json`~`v12.json`, 12파일·1,800 records, `S1-CTH-0001`~`S1-CTH-1800` 연속.
- source 구성: 다섯 편집 유형 `causal_context`, `role_coordination`, `temporal_dependency`, `resource_constraint`, `reference_resolution`을 각각 360 records로 균등 배치했다. JSON에는 이 편집 유형을 넣지 않고 통제 relation만 기록했다.
- relation 분포: `is_a` 0, `subclass_of` 0, `part_of` 145, `classification` 334, `boundary` 815, `contrast` 160, `comparison` 93, `function` 611, `role` 533, `process` 954, `state` 1,519, `attribute` 236, `other` 1,800.
- 텍스트 규모: 140,702 characters, 29,367 whitespace word units. 길이는 최소 55자, 중앙값 79자, 평균 78.168자, 최대 97자다. 모든 record는 직접 작성 원문이며 source와 JSON 텍스트가 일치한다.
- 최종 감사: schema·metadata·relation·source parse·source/JSON 불일치·ID/primary/text/concept-relation 중복·제어/이상 문자·5어절 반복·개념 조사 문제 모두 0건. 광범위 조사 후보 3건은 `관계없는`, `전문가`, `손상평가`의 정상 어휘 오탐이다.
- 유사도: 현 영역 내부 최고 0.359749, 기존 고밀도 train/val과의 최고 0.184556. 저밀도와 held-out은 비교 대상에서 제외했다.
- 확정 감사 파일: `audit_reports/machine/TinyLM_Stage1_Context_Train_v01_v12_Final_Audit_2026-09-01.json`, 통합 보고서 `audit_reports/Stage1_(9)_Context_Consolidated_Audit.md`.
- 이 절의 v01~v12 JSON과 대응 TSV는 확정 보호 대상으로 취급하며 후속 영역 생성 중 수정하지 않는다.

## 20. Stage1 (10) 타입·부정·불확실성 train 설계 원장

```text
목표: 1,350 records = 9 files × 150 / 약 120K
파일: stage1_(10)type_uncertainty_high_density_train_v01.json ... v09.json
ID: S1-TUH-0001 ... S1-TUH-1350
type/split: type_uncertainty_packet / train
핵심 오류 억제: 타입과 값의 혼동, 부정 범위 오독, 부재·0·빈 값·비존재의 동일시, 미관측을 거짓으로 단정, 가능성을 사실로 승격
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 클래스·인스턴스·토큰·식별자·메타타입 구분 | 유형/사례, 대상/이름, 값/표현, 스키마, 메타 수준 | 확정 |
| v02 | 0151~0300 | Entity·Attribute·Quantity·Relation·State·Action 타입 구분 | 대상, 속성, 수량, 관계, 상태, 행동의 정보형 판정 | 확정 |
| v03 | 0301~0450 | 한국어 명제 부정·부분 부정·양화·범위 해석 | 아니다/않다, 모두 아님, 하나도 없음, 오직, 이중 부정 | 확정 |
| v04 | 0451~0600 | 부재·비존재·빈값·0·삭제·접근불가 구분 | 없음의 종류, 빈 용기, 영 수량, 삭제 상태, 권한·접근 실패 | 확정 |
| v05 | 0601~0750 | 미관측·미측정·미기록·미응답·알수없음 구분 | 센서 공백, 조사 누락, 기록 부재, 응답 거절, 지식 한계 | 확정 |
| v06 | 0751~0900 | 가능성·확률·확신·추정·증거 강도의 구분 | 가능/개연, 확률값, 신뢰구간, 주관 확신, 근거 수준 | 확정 |
| v07 | 0901~1050 | 상충·불완전·모호·오래된 출처의 불확실성 통합 | 출처 충돌, 누락, 용어 모호성, 시점 불일치, 갱신 필요 | 확정 |
| v08 | 1051~1200 | 센서·검사·탐지의 양성·음성·오탐·미탐·검출한계 | 참/거짓 양성·음성, 민감도, 기저율, 경계값, 불확정 | 확정 |
| v09 | 1201~1350 | 계획·예측·가정·시뮬레이션·반사실과 실제 사건 구분 | 예정/발생, 예측/관측, 가정 조건, 모의 결과, 반사실 | 확정 |

### 20.1 생성·감사 확정 기록 (2026-09-01)

- 산출물: `stage1_(10)type_uncertainty_high_density_train_v01.json`~`v09.json`, 9파일·1,350 records, `S1-TUH-0001`~`S1-TUH-1350` 연속.
- source 구성: 다섯 편집 유형 `metatype_reference`, `negation_scope`, `absence_nonexistence`, `unknown_unobserved`, `uncertainty_evidence`를 각각 270 records로 균등 배치했다. JSON에는 편집 유형을 넣지 않고 통제 relation만 기록했다.
- relation 분포: `is_a` 0, `subclass_of` 0, `part_of` 17, `classification` 486, `boundary` 1,350, `contrast` 1, `comparison` 144, `function` 3, `role` 31, `process` 217, `state` 1,136, `attribute` 361, `other` 1,350.
- 텍스트 규모: 100,895 characters, 22,940 whitespace word units. 길이는 최소 55자, 중앙값 75자, 평균 74.737자, 최대 103자다. 모든 record는 직접 작성 원문이며 source와 JSON 텍스트가 일치한다.
- 최종 감사: schema·metadata·relation·source parse·source/JSON 불일치·ID/primary/text/concept-relation 중복·제어문자·5어절 반복·반복 시작구·개념 조사 문제 모두 0건.
- 이상 문자 후보 1건은 오차 범위를 나타내는 정상 기호 `±`이고, 광범위 조사 후보 9건은 `뒤집는`, `비전문가`, `모르겠는가`, `무엇인가`, `영측정센서바닥효과`, `전문가`의 정상 형태에 대한 오탐이다.
- 문자 3~5-gram TF-IDF cosine 상한은 내부 0.392918, 기존 고밀도 train/val 교차 0.289830이다. 저밀도와 held-out은 비교 대상에서 제외했다.
- 확정 감사 파일: `audit_reports/machine/TinyLM_Stage1_TypeUncertainty_Train_v01_v09_Final_Audit_2026-09-01.json`, 통합 보고서 `audit_reports/Stage1_(10)_TypeUncertainty_Consolidated_Audit.md`.
- 이 절의 v01~v09 JSON과 대응 TSV는 확정 보호 대상으로 취급하며 후속 영역 생성 중 수정하지 않는다.

## 21. Stage1 (5)~(10) validation 공통 등록

사용자 지정 validation 총량은 1,950 records, 13 files이며 모든 파일은 정확히 150 records와 하나의 신규 concept family를 담는다. 저밀도 데이터셋과 held-out benchmark는 family 선정·문장 작성·중복 비교의 근거로 쓰지 않는다. 각 영역의 train 정본과 기존 고밀도 validation만 분리 기준으로 삼는다.

| 영역 | slug / type | ID prefix | 목표 | 설계량 | version |
|---|---|---|---:|---:|---|
| (5) 부분–전체 | `partwhole` / `partwhole_packet` | `S1-PWV-` | 450 = 3×150 | 약 30K | v01~v03 |
| (6) 상태·상태 변화 | `statechange` / `statechange_packet` | `S1-SCV-` | 450 = 3×150 | 약 30K | v01~v03 |
| (7) 공간 관계 | `spatial` / `spatial_packet` | `S1-SPV-` | 300 = 2×150 | 약 21K | v01~v02 |
| (8) 비교·대조 | `comparison` / `comparison_packet` | `S1-COV-` | 300 = 2×150 | 약 18K | v01~v02 |
| (9) 문맥 통합 | `context` / `context_packet` | `S1-CTV-` | 300 = 2×150 | 약 15K | v01~v02 |
| (10) 타입·부정·불확실성 | `type_uncertainty` / `type_uncertainty_packet` | `S1-TUV-` | 150 = 1×150 | 약 12K | v01 |

파일명은 `stage1_(N)<slug>_high_density_val_vNN.json` 형식이다. record key는 `id`, `type`, `split`, `text`, `concepts`, `relations`, `unseen_relation`만 허용하고 `split`은 `val`이다. relation은 13개 통제 어휘에서 2~5개를 중복 없이 사용하며 각 영역의 train 의미 규약도 그대로 적용한다.

### 21.1 train–validation 분리와 일반화 slice

- train과 정확히 같은 `text`, primary concept, `primary concept + 정렬 relation-set` 조합을 금지한다.
- train 문장을 단순 치환·어순 변경한 문장과 공통 5어절 연쇄를 금지하고, 내부 및 기존 고밀도 전체와의 문자 3~5-gram 유사도 상위 쌍을 사람이 검토한다.
- `unseen_relation: false`는 해당 영역 train에 관측된 정렬 relation-set만 쓴다.
- `unseen_relation: true`는 개별 relation 이름은 해당 영역 train에 이미 관측되었지만, 그 정렬 relation-set 조합은 해당 영역 train에 없도록 한다. 이는 통제 어휘 밖의 새 이름을 뜻하지 않는다.
- 각 파일은 true 18개, false 132개로 고정한다. 전체 true는 234/1,950 = 12.00%이며 사용자 지정 10~15% 범위 안이다.
- true/false 어느 쪽도 train과 같은 교육 객체를 재사용하지 않는다. family가 새롭더라도 세부 primary concept가 기존 고밀도와 겹치면 직접 교체한다.

## 22. Stage1 (5) 부분–전체 validation 설계 원장

```text
파일: stage1_(5)partwhole_high_density_val_v01.json ... v03.json
ID: S1-PWV-0001 ... S1-PWV-0450
type/split: partwhole_packet / val
필수 의미: 모든 record에 part_of, 부분과 전체의 방향 및 상속 한계 명시
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 도서관 장서·서지레코드·권호·대출 단위 구성 | 컬렉션/자료, 서지/판·권호, 권/복본, 청구기호, 대출 묶음 | 확정 |
| v02 | 0151~0300 | 의류 패턴·재단 조각·봉제 부품·완제품 구성 | 패턴/조각, 몸판·소매, 여밈·안감, 봉제선, 세트/단품 | 확정 |
| v03 | 0301~0450 | 우편물·행낭·운송편·배달구역 물류 구성 | 내용물/우편물, 묶음/행낭, 행낭/운송편, 구역/경로, 배달 단위 | 확정 |

## 23. Stage1 (6) 상태·상태 변화 validation 설계 원장

```text
파일: stage1_(6)statechange_high_density_val_v01.json ... v03.json
ID: S1-SCV-0001 ... S1-SCV-0450
type/split: statechange_packet / val
필수 의미: 모든 record에 state와 process, 전후 상태와 전이 조건 명시
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 박물관 유물 보존처리·안정화·복원·수장 상태 변화 | 입수·격리, 조사, 세척·안정화, 복원, 전시·수장 전환 | 확정 |
| v02 | 0151~0300 | 공연 제작·연습·무대전환·개막·철거 상태 변화 | 기획·캐스팅, 연습, 기술 리허설, 공연, 장면 전환·철거 | 확정 |
| v03 | 0301~0450 | 법원 사건 접수·배당·심리·판결·종결 상태 변화 | 접수·보정, 배당, 송달, 심리, 선고·확정·종결 | 확정 |

## 24. Stage1 (7) 공간 관계 validation 설계 원장

```text
파일: stage1_(7)spatial_high_density_val_v01.json ... v02.json
ID: S1-SPV-0001 ... S1-SPV-0300
type/split: spatial_packet / val
필수 의미: 모든 record에 other; 부분 관계와 단순 위치를 구별
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 스포츠 경기장·코트·선수·공·판정구역 공간 관계 | 선 안팎, 진영, 선수 기준 좌우, 공의 접촉·가림, 판정 기준면 | 확정 |
| v02 | 0151~0300 | 지하광산 갱도·작업면·환기구·운반로 공간 관계 | 갱구 기준 깊이, 상·하부 갱도, 교차·분기, 통기 연결, 대피 거리 | 확정 |

## 25. Stage1 (8) 비교·대조 validation 설계 원장

```text
파일: stage1_(8)comparison_high_density_val_v01.json ... v02.json
ID: S1-COV-0001 ... S1-COV-0300
type/split: comparison_packet / val
필수 의미: 모든 record에 comparison 또는 contrast; 비교 축·단위·조건 명시
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 음악 연주·녹음의 음높이·음량·템포·균형 비교 | 기준음, 상대 음량, 평균/순간 템포, 음색, 채널·공간 균형 | 확정 |
| v02 | 0151~0300 | 농산물 경매·품질등급·가격·수율·보관성 비교 | 규격·등급, 단위가격, 수율, 결점률, 저장 조건·기간 | 확정 |

## 26. Stage1 (9) 문맥 통합 validation 설계 원장

```text
파일: stage1_(9)context_high_density_val_v01.json ... v02.json
ID: S1-CTV-0001 ... S1-CTV-0300
type/split: context_packet / val
필수 의미: 3~6개 literal concept와 3~5개 relation으로 사람·대상·위치·시간·행동·결과 연결
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 영화 촬영 현장의 장면·배우·소품·카메라·촬영순서 상황 | 콜시트, 배우, 소품, 카메라, 테이크, 연속성·재촬영 | 확정 |
| v02 | 0151~0300 | 선거 투표소의 유권자·명부·투표용지·투표함·참관 상황 | 신원 확인, 명부, 용지 교부, 기표·투입, 참관·마감 | 확정 |

## 27. Stage1 (10) 타입·부정·불확실성 validation 설계 원장

```text
파일: stage1_(10)type_uncertainty_high_density_val_v01.json
ID: S1-TUV-0001 ... S1-TUV-0150
type/split: type_uncertainty_packet / val
필수 의미: 모든 record에 other와 classification·boundary·state 중 하나 이상
```

| version | ID 범위 | 예약 concept family | 포함 축 | 상태 |
|---|---|---|---|---|
| v01 | 0001~0150 | 역사연구 사료·증언·연대추정·번역·복원가설 불확실성 판정 | 사료 유형/내용, 부정 범위, 침묵·부재, 연대 구간, 출처 충돌·가설 | 확정 |

## 28. Stage1 (5)~(10) validation 생성·최종 감사 확정 기록 — 2026-09-01

§21~§27의 예약 원장대로 13개 신규 concept family를 실제 파일로 확정했다. 총량은 13 files, 1,950 records, 154,038자, 정규식 분리 단위 34,635개다. 모든 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개를 담는다. 따라서 일반화 slice는 영역별·파일별 12.00%, 전체 234/1,950 = 12.00%다.

| 영역 | 파일/records | ID | 문자/단어 단위 | unseen | validation 내부 최대 cosine | train 교차 최대 cosine |
|---|---:|---|---:|---:|---:|---:|
| (5) 부분–전체 | 3 / 450 | `S1-PWV-0001`~`0450` | 36,250 / 8,456 | 54 | 0.262881 | 0.134686 |
| (6) 상태·상태 변화 | 3 / 450 | `S1-SCV-0001`~`0450` | 34,439 / 7,622 | 54 | 0.267992 | 0.144340 |
| (7) 공간 관계 | 2 / 300 | `S1-SPV-0001`~`0300` | 22,753 / 5,211 | 36 | 0.314553 | 0.184022 |
| (8) 비교·대조 | 2 / 300 | `S1-COV-0001`~`0300` | 22,660 / 5,206 | 36 | 0.222778 | 0.174069 |
| (9) 문맥 통합 | 2 / 300 | `S1-CTV-0001`~`0300` | 23,890 / 4,858 | 36 | 0.260654 | 0.101915 |
| (10) 타입·부정·불확실성 | 1 / 150 | `S1-TUV-0001`~`0150` | 14,046 / 3,282 | 18 | 0.099034 | 0.130310 |

validation 전체 relations 분포는 `is_a` 0, `subclass_of` 0, `part_of` 454, `classification` 470, `boundary` 698, `contrast` 153, `comparison` 304, `function` 691, `role` 238, `process` 888, `state` 1,094, `attribute` 357, `other` 1,155다. 0회 relation도 누락하지 않았고, 모든 record는 13개 통제 어휘에서 2~5개를 중복 없이 사용한다.

`other` 편집 유형 상위 5개는 다음과 같다.

- (5): 기록 범위·단위 6, 컬렉션 소속·묶음 5, 선택적 구성요소 5, 구성원 예외·비소속 5, 운반체·내용물 범위 4.
- (6): 측정 한계 4, 관찰·모니터링 불확실성 3, 출처·이력 검토 2, 목록·재고 예외 2, 복원 가설 2.
- (7): 포함·위치, 방향·순서, 인접·연결, 거리·근접, 기준계·투영이 각각 60.
- (8): 참조 기준 정규화, 다차원 순위, 상황 의존 순위, 불확실성 구간, 질적 대조가 각각 60.
- (9): 인과 맥락, 역할 조정, 시간 의존, 자원 제약, 지시 대상 복원이 각각 60.
- (10): 사료 유형·참조 단위, 부정 범위, 기록의 공백·침묵, 연대 구간·시간 추정, 가설·증거 강도가 각각 30.

최종 통합 감사는 JSON/UTF-8/schema/metadata/ID/source 대응/relations 오류 0, exact ID·primary concept·text·primary–relation-set 중복 0, 대응 train 및 외부 고밀도와의 exact overlap 0을 확인했다. 초안에서 발견한 validation 내부 반복 5어절 13건과 외부 고밀도 교차 5어절 2건은 해당 문장을 직접 다시 표현한 뒤 모두 0건으로 재감사했다. validation 전체 문자 3~5-gram TF-IDF cosine 최대는 0.311151이며 검토 기준 0.72 이상 쌍은 내부와 대응 train 교차 모두 0건이다. primary concept 직결 조사 오류는 0건이다. 광역 조사 후보 25건은 `맞닿는`, `가까이`, `물려받는` 등 정상 용언·복합어·외래어에 대한 자동 탐지 오탐으로 원문 확인했다.

작업 시작 시 존재한 train/val JSON 242개는 종료 시점 SHA-256 대조에서 242/242가 일치했고 변경·누락은 0건이다. 새로 추가된 JSON은 §22~§27의 validation 13개뿐이다. 세부 해시 근거는 `audit_reports/machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`에 보존한다.

`unseen_relation: true`의 모든 개별 label은 대응 train에 이미 있고 정렬 relation-set 조합만 train에 없다. false의 relation-set은 모두 train에 있다. 저밀도와 held-out/evaluation corpus는 생성·family 선정·유사도 비교에서 제외했다.

사람용 정본은 `audit_reports/README.md`와 영역별 통합 보고서 6개다. 기계 감사는 `audit_reports/machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`, 과거 진행 감사·보고서는 `audit_reports/archive/`에 보존한다. 생성 source는 `tools/stage1_relational_validation_sources/<slug>/vNN.tsv`, 패키징은 `tools/build_stage1_relational_validation.py`, 재감사는 `tools/audit_stage1_relational_validation.py`를 사용한다. §9에 등록된 새 validation 13파일은 이 절 이후 수정 금지다.


## 29. Stage 2~10 공통 3M 준비 기준 — 역사적 primary·pilot 기준선

2026-09-01 사용자 지시에 따라 Stage 2~10의 상위 역할을 세부 교육영역·비율·파일 namespace·ID prefix·150-record concept-family 원장으로 구체화했다. 2026-09-02에는 이 설계의 tokenizer gate용 pilot을 Stage별 4 files·600 records씩 완료했다. 이 절부터 §39까지의 250 primary·25 contingency 수치와 “승인 대기” 문맥은 실측 3M 승인 전 준비 기준선을 설명한다. 현행 승인 총량·완전 예약·생성 진행률은 §40과 작업원장을 우선하며, Stage별 전체 corpus는 아직 완료되지 않았다.

### 29.1 권고 split과 총량

| 항목 | Stage별 준비값 | 판정 |
|---|---:|---|
| 설계 목표 | 약 3,000,000 token | pilot 실측 완료, §40의 실제 파일 수 승인 완료 |
| primary 전체 | 250 files / 37,500 records | 한 파일 150 records |
| train | 225 files / 33,750 records | 90% |
| validation | 25 files / 3,750 records | 10% |
| validation 일반화 slice | 파일당 18/150 | 12.00% |
| contingency reserve | 25 family | 준비 당시 비활성; 현행은 Stage별 25개 모두 배치·활성화 |
| 완료 pilot | Stage별 4 files / 600 records | A01·A03·A06 train v01 + A01 val v01 |
| pilot 실측 tokenizer | `tok-ko-en-32768.json` + record별 EOS 1개 | TinyLM CLI 기본 `--data ko-en` 대응 |

90:10을 전체 생성 split로 확정했다. 150-record 단위에서 정확한 비율을 유지하고 checkpoint 선택용 validation을 충분히 확보할 수 있기 때문이다. 최종 파일 수와 split 배분은 §40의 실제 tokenizer 실측안으로 사용자 승인을 받았다. 최종 blind held-out은 이 약 3M 안에 섞지 않고 별도로 동결한다. 90/8/2처럼 blind slice를 내부에 두는 안은 Guide의 held-out 경계를 바꾸므로 별도 승인 없이는 채택하지 않는다.

Stage1 고밀도 실제값은 255 files, 38,200 records, text 2,886,573자, 평균 75.565자다. 250 files·37,500 records는 평균 80자일 때 3M **문자 proxy**일 뿐 tokenizer token 수가 아니다.

### 29.2 tokenizer 보정 gate

각 Stage에서 교육 성격이 다른 A01·A03·A06 train v01과 A01 validation v01, 총 4 files·600 records를 먼저 직접 작성·감사한다. 실제 학습 tokenizer로 평균 token/record를 잰 뒤 다음 식을 사용한다.

```text
raw_files = round(3,000,000 / measured_mean_tokens_per_record / 150)
exact_90_10_files = 10 × round(raw_files / 10)
```

이 gate는 2026-09-02에 9개 Stage 모두 완료했다. `tok-ko-en-32768.json`의 pure ByteLevel-BPE token 수에 학습 경로와 동일한 EOS 1개/record를 더해 5,400 records를 측정했고, 별도 Python 3.11.4·`tokenizers 0.22.2` 구현과 record별로 대조해 mismatch 0·최대 차이 0을 확인했다. 전체 pilot은 224,631 tokens, 평균 41.598333 tokens/record다. Stage별 평균과 배분 후보는 §40에 기록한다.

실측 부족분은 사용자 승인 뒤 기존 250 primary와 25 contingency 범위를 넘어 Stage별 필요한 family를 추가 예약했다. primary tail은 삭제하지 않았고, 37,500 records를 3M token이라고 보고하지 않는다. 후속 전체 작업 승인 뒤 pilot 다음 corpus 생성은 직접 작성 방식으로 착수했다.

### 29.3 공통 schema·분리

- 파일명은 `stageN_(M)<slug>_high_density_{train,val}_vNN.json`, version은 영역별 v01부터 시작한다. `vNN`은 최소 두 자리 표기이며 v99를 넘으면 v100·v101처럼 자릿수를 확장한다.
- Stage2 신규 영역은 보호된 legacy `stage2_(2)attribute_high_density_*`와 충돌하지 않도록 파일 slot `(11)`~`(16)`을 사용한다. legacy pattern은 새 3M mixture에서 제외하고 수정·이름변경·재생성하지 않는다.
- Stage3~10은 파일 slot `(1)`~`(6)`을 사용한다.
- 신규 ID는 `S<Stage>-<AreaCode>H-00001` / `S<Stage>-<AreaCode>V-00001`의 5자리 번호다.
- relation은 Guide §9의 13개 통제 어휘에서 의미가 실제 문장에 있는 2~5개를 record 안 중복 없이 사용한다.
- validation false는 train 관측 relation 이름·정렬 relation-set을 사용하고, true 12%는 통제 어휘를 벗어나지 않는 train 미관측 relation-set 조합을 원칙으로 한다. 실제 train에 통제 label 결측이 있으면 Guide §13에 따라 해석을 먼저 등록한다.
- validation의 모든 개별 relation label은 해당 Stage train에서 관측되어야 한다. `unseen_relation: true`는 최대 3개까지만 연속 배치하고, 30-record 단위 다섯 구간마다 최소 2개를 분산한다.
- validation의 domain bank, primary concept, exact text, primary+relation-set과 5어절 문구는 train과 분리한다.
- 중앙 원장의 `relation_focus`는 영역 수준 편집 초점이지 record별 필수 교집합이나 허용 목록이 아니다. 문장에 거짓 relation을 넣어 분포를 맞추지 않는다.
- family 이름은 topic 경계이지 text template가 아니다. corpus 의미 문장은 record마다 직접 작성한다.

## 30. Stage 2 — 복합 관계·의존·인과·조건 구조

조건부 관계, 원인–결과, 의존성, 가능성, 시간적 선후, 상태 전이와 다중 관계 조합을 분리·결합한다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 11 | 원인 구조 / `causal_structure` | 20% | 600,000 | 45/5 | `causal_structure_packet` | `S2-CSH` / `S2-CSV` | 원인·결과·매개·공통 원인을 개입과 관찰의 차이까지 포함해 판정한다. | 상관을 인과로 승격, 결과 뒤 사건을 원인으로 단정, 단일 원인 과장 |
| 2 / 12 | 조건·의존 구조 / `conditional_dependency` | 20% | 600,000 | 45/5 | `conditional_dependency_packet` | `S2-CDH` / `S2-CDV` | 필요조건·충분조건·선행 의존·예외 범위를 실제 결과와 분리한다. | 필요와 충분의 역전, 기본값을 무조건 규칙으로 확대, 의존 방향 반전 |
| 3 / 13 | 시간 순서·간격 / `temporal_order` | 16% | 480,000 | 36/4 | `temporal_order_packet` | `S2-TOH` / `S2-TOV` | 사건의 선후·동시성·기간·지연·관측 창을 구별한다. | 서술 순서를 사건 순서로 오독, 겹친 기간을 동일 시점으로 단정 |
| 4 / 14 | 상태 전이·동역학 / `state_transition` | 16% | 480,000 | 36/4 | `state_transition_packet` | `S2-STH` / `S2-STV` | 전이 전후 상태, 촉발·억제 조건, 중간 상태와 가역성을 연결한다. | 상태를 정체성으로 고정, 중간 상태 생략, 가역·비가역 혼동 |
| 5 / 15 | 가능성·양상 / `modality_possibility` | 16% | 480,000 | 36/4 | `modality_possibility_packet` | `S2-MPH` / `S2-MPV` | 가능·예정·예측·확률·확신·반사실을 실제 발생과 분리한다. | 가능성을 사실로 승격, 계획과 예측 혼동, 확신을 확률로 치환 |
| 6 / 16 | 다중 관계 조합 / `relational_composition` | 12% | 360,000 | 27/3 | `relational_composition_packet` | `S2-RCH` / `S2-RCV` | 여러 객체와 관계를 다단 연결하면서 충돌·누락·우선순위를 보존한다. | 한 관계를 전체 경로에 전이, 국소 사실로 전역 결론, 충돌 정보 은폐 |

- train 객체·상황 bank: 스마트 온실 관수·환경제어, 도시 상수도 정수·배수 운영, 클라우드 서비스 부하·장애 대응, 철도 운행 간격·환승 조정, 하천 저수지 수위·방류 관리, 식품 냉장 유통·품질 유지, 온라인 학습 진도·피드백 운영, 생태 복원지 종·서식지 관찰, 배터리 저장장치 충방전·열관리
- validation 신규 객체·상황 bank: 문화재 수장고 온습도·보존 운영, 양봉 군체 활동·질병 관리, 해저 통신케이블 장애·복구, 공연장 입장·좌석·대피 운영, 고산 구조대 탐색·후송 상황
- pilot 예약: `S2-A01-T-001`, `S2-A03-T-001`, `S2-A06-T-001`, `S2-A01-V-001`
- contingency domain bank: 지하철 역사 환기·혼잡 제어, 수산 양식장 수질·급이 운영, 태양광 발전소 출력·고장 관리, 응급 콜센터 배차·인계, 도심 빗물저류·침수 대응
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 480 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 31. Stage 3 — 절차·행동·계획·문제 해결

목표, 계획, 단계, 제약, 자원, 선택, 우선순위, 실패와 복구를 행동 전후 상태와 연결한다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 목표·행동 연결 / `goal_action` | 20% | 600,000 | 45/5 | `goal_action_packet` | `S3-GAH` / `S3-GAV` | 명시 목표와 하위 목표, 행동 수단과 결과 상태를 연결한다. | 행동 자체를 목표로 오독, 수단과 성과 동일시, 부수 효과 누락 |
| 2 / 2 | 절차·순서 / `procedure_sequence` | 20% | 600,000 | 45/5 | `procedure_sequence_packet` | `S3-PSH` / `S3-PSV` | 선행조건과 단계 순서, 병렬 가능 단계, 확인 지점을 구조화한다. | 단계 누락, 순서 임의 교환, 병렬·직렬 혼동 |
| 3 / 3 | 계획 분해 / `planning_decomposition` | 16% | 480,000 | 36/4 | `planning_decomposition_packet` | `S3-PDH` / `S3-PDV` | 큰 목표를 검증 가능한 작업과 의존성으로 분해하고 재계획한다. | 과도하게 큰 작업, 의존 누락, 계획과 실행 로그 혼동 |
| 4 / 4 | 제약·자원 / `constraint_resource` | 16% | 480,000 | 36/4 | `constraint_resource_packet` | `S3-CRH` / `S3-CRV` | 시간·용량·권한·안전 제약과 소모·재사용 자원을 구분한다. | 희망사항을 제약으로 오독, 자원 중복 계산, 안전 제약 완화 |
| 5 / 5 | 선택·우선순위 / `decision_priority` | 16% | 480,000 | 36/4 | `decision_priority_packet` | `S3-DPH` / `S3-DPV` | 여러 대안의 비용·효용·위험·가역성을 기준에 맞춰 선택한다. | 한 축 우위를 전체 우위로 확대, 매몰비용 고착, 기준 변경 은폐 |
| 6 / 6 | 실행 감시·실패 복구 / `execution_recovery` | 12% | 360,000 | 27/3 | `execution_recovery_packet` | `S3-ERH` / `S3-ERV` | 진행 상태, 실패 징후, 재시도·롤백·우회와 종료 판단을 연결한다. | 실패를 성공으로 보고, 무한 재시도, 복구 뒤 검증 생략 |

- train 객체·상황 bank: 목공 가구 제작, 실험실 시료 분석, 지역 축제 운영, 전자상거래 창고 출고, 소프트웨어 릴리스, 산불 초기 대응, 다도시 여행 일정, 밭작물 파종·관개, 외래 진료 예약·검사
- validation 신규 객체·상황 bank: 수중 다큐멘터리 촬영, 고문서 복원 작업, 드론 지형 측량, 이동식 급식소 운영, 천체 관측 캠페인
- pilot 예약: `S3-A01-T-001`, `S3-A03-T-001`, `S3-A06-T-001`, `S3-A01-V-001`
- contingency domain bank: 유리공예 제작, 이동형 도서관 운영, 해양 시료 채취, 야외 음악회 운영, 소형위성 조립
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 470 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 32. Stage 4 — 문맥·담화·지시·대화

장문 참조, 생략, 대화 상태, 질문–응답, 지시 추적, 화행, 암시와 맥락 의존을 다룬다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 담화 지시·참조 / `discourse_reference` | 20% | 600,000 | 45/5 | `discourse_reference_packet` | `S4-DRH` / `S4-DRV` | 명사구·대명사·지시어의 선행 대상을 거리와 담화 중심 변화 속에서 추적한다. | 가까운 명사를 무조건 선행사로 선택, 화제 전환 누락 |
| 2 / 2 | 생략·공동지시 / `ellipsis_coreference` | 20% | 600,000 | 45/5 | `ellipsis_coreference_packet` | `S4-ECH` / `S4-ECV` | 한국어 생략 성분과 반복 명칭의 동일·비동일 대상을 문맥으로 복원한다. | 주어·목적어 임의 보충, 같은 표현을 같은 객체로 자동 합치기 |
| 3 / 3 | 대화 상태 / `dialogue_state` | 16% | 480,000 | 36/4 | `dialogue_state_packet` | `S4-DSH` / `S4-DSV` | 참여자 목표, 합의·미합의, 열린 질문, 약속과 수정 이력을 유지한다. | 철회된 합의를 유지, 미답 질문을 완료 처리, 화자 역할 혼동 |
| 4 / 4 | 질문–응답 적합성 / `question_answer` | 16% | 480,000 | 36/4 | `question_answer_packet` | `S4-QAH` / `S4-QAV` | 질문의 초점·범위·전제에 맞는 답과 미답·부분답·회피를 구분한다. | 관련 정보만 있으면 답으로 인정, 거짓 전제 수용, 범위 초과 |
| 5 / 5 | 화행·대화 행위 / `speech_act_pragmatics` | 16% | 480,000 | 36/4 | `speech_act_pragmatics_packet` | `S4-SPH` / `S4-SPV` | 진술·질문·요청·약속·경고·허가의 기능과 조건을 판정한다. | 문장형만으로 화행 결정, 권고를 명령으로 확대, 권한 누락 |
| 6 / 6 | 함축·맥락 의존 / `implicature_context` | 12% | 360,000 | 27/3 | `implicature_context_packet` | `S4-ICH` / `S4-ICV` | 말한 내용과 함축, 관례·공유 지식·상황에 의존한 해석을 분리한다. | 함축을 문자적 사실로 기록, 풍자·완곡 표현 과잉 확정 |

- train 객체·상황 bank: 심리상담 초기면담, 전자제품 고객지원, 과학 수업 토론, 설비 교대 일지, 프로젝트 의사결정 회의, 온라인 기사 정정과 댓글, 국제여행 안내 창구, 행정 민원 보완 대화, 협동 게임 팀 소통
- validation 신규 객체·상황 bank: 고고학 구술 인터뷰, 국제회의 동시통역, 미술관 도슨트 문답, 선박 해상무선 교신, 지역사 구술채록 검증
- pilot 예약: `S4-A01-T-001`, `S4-A03-T-001`, `S4-A06-T-001`, `S4-A01-V-001`
- contingency domain bank: 재난현장 브리핑, 항공관제 교신, 언어교환 수업, 생방송 인터뷰, 공동주택 주민회의
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 440 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 33. Stage 5 — 일반화·추론·전이

귀납·연역 구조, 반례 기반 일반화, 새로운 개념 조합, 규칙·구조의 다른 도메인 전이를 다룬다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 귀납 일반화 / `induction` | 20% | 600,000 | 45/5 | `induction_packet` | `S5-INH` / `S5-INV` | 표본에서 규칙을 제안하되 범위·대표성·불확실성을 함께 유지한다. | 소표본을 보편 법칙으로 확대, 선택 편향·기저율 무시 |
| 2 / 2 | 연역 추론 / `deduction` | 20% | 600,000 | 45/5 | `deduction_packet` | `S5-DEH` / `S5-DEV` | 규칙·전제·조건에서 유효 결론을 도출하고 불충분 전제를 식별한다. | 결과 긍정·전건 부정, 암묵 전제 삽입, 양화 범위 오류 |
| 3 / 3 | 반례 기반 일반화 / `counterexample_generalization` | 16% | 480,000 | 36/4 | `counterexample_generalization_packet` | `S5-CGH` / `S5-CGV` | 반례가 규칙 전체·범위·조건 중 무엇을 수정하는지 판정한다. | 예외 하나로 모든 경향 폐기, 반례를 무시, 조건을 사후 부착 |
| 4 / 4 | 새 조합 일반화 / `compositional_novelty` | 16% | 480,000 | 36/4 | `compositional_novelty_packet` | `S5-CNH` / `S5-CNV` | 학습한 개념·관계를 새로운 조합에 적용하되 구성 요소 역할을 보존한다. | 함께 등장한 개념 동일시, 한 구성의 관계를 다른 구성에 복사 |
| 5 / 5 | 유추 전이 / `analogical_transfer` | 16% | 480,000 | 36/4 | `analogical_transfer_packet` | `S5-ATH` / `S5-ATV` | 표면 유사성과 구조 대응을 구분하고 대응 가능한 관계만 전이한다. | 어휘 유사성만으로 전이, 관계 대응 뒤 속성까지 무조건 복사 |
| 6 / 6 | 도메인 구조 전이 / `structural_transfer` | 12% | 360,000 | 27/3 | `structural_transfer_packet` | `S5-STH` / `S5-STV` | 한 도메인의 규칙·제약·계층을 다른 도메인에 적용하고 불변·변경 요소를 표시한다. | 도메인 고유 제약 누락, 명칭만 바꾼 모사, 단위·척도 무시 |

- train 객체·상황 bank: 신소재 내구성 시험, 작물 품종 수확량 분석, 야생동물 개체군 조사, 검색 알고리즘 성능 평가, 대중교통 수요 변화, 지역 전력 사용 예측, 방언 변화 자료 분석, 소액대출 위험 분석, 제조 공정 불량 분석
- validation 신규 객체·상황 bank: 산호초 회복 조사, 필사본 연대 추정, 외계행성 후보 분류, 전통 유약 소성 분석, 도시 열섬 완화 평가
- pilot 예약: `S5-A01-T-001`, `S5-A03-T-001`, `S5-A06-T-001`, `S5-A01-V-001`
- contingency domain bank: 고래 음향자료 분석, 고대 동전 분류, 화산 가스 변화 예측, 농촌 인구 이동 분석, 로봇 파지 성능 시험
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 600 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 34. Stage 6 — 지식 통합·장문맥·복합 문제

긴 문맥, 다단계 추론, 복합 제약, 다중 목표, 정보 통합과 불확실성 관리를 다룬다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 장문맥 유지 / `long_context` | 20% | 600,000 | 45/5 | `long_context_packet` | `S6-LCH` / `S6-LCV` | 긴 문서의 인물·객체·시점·정의·변경 이력을 압축 없이 유지한다. | 초반 사실 망각, 동명이인 합치기, 최신 정정 이전 정보 사용 |
| 2 / 2 | 다단계 추론 / `multihop_inference` | 20% | 600,000 | 45/5 | `multihop_inference_packet` | `S6-MHH` / `S6-MHV` | 흩어진 전제를 연결해 중간 결론과 최종 결론의 근거 경로를 보존한다. | 중간 단계 생략, 다른 경로의 전제 혼합, 결론 순환 |
| 3 / 3 | 복합 제약 만족 / `constraint_satisfaction` | 16% | 480,000 | 36/4 | `constraint_satisfaction_packet` | `S6-CSH` / `S6-CSV` | 동시 제약의 충돌·우선순위·완화 가능성을 판정해 가능한 해를 찾는다. | 일부 제약 누락, 선호와 강제 제약 혼동, 숨은 충돌 방치 |
| 4 / 4 | 다중 목표·절충 / `multiobjective_tradeoff` | 16% | 480,000 | 36/4 | `multiobjective_tradeoff_packet` | `S6-MTH` / `S6-MTV` | 상충 목표의 지표·가중·하한과 절충을 언어적으로 판단한다. | 단일 점수로 모든 목표 은폐, 하한 위반, 한 집단 효용만 최적화 |
| 5 / 5 | 다중 출처 통합 / `multisource_integration` | 16% | 480,000 | 36/4 | `multisource_integration_packet` | `S6-MIH` / `S6-MIV` | 출처별 범위·시점·신뢰도·중복·충돌을 판정해 통합한다. | 출처 수를 신뢰도로 대체, 최신성만으로 우위, 중복 증거 이중 계산 |
| 6 / 6 | 불확실성 관리 / `uncertainty_management` | 12% | 360,000 | 27/3 | `uncertainty_management_packet` | `S6-UMH` / `S6-UMV` | 미지·누락·측정오차·모델 불확실성을 구분하고 결정에 반영한다. | 모든 불확실성을 하나로 합치기, 미관측을 0으로 치환, 과잉 확신 |

- train 객체·상황 bank: 광역 재난 자원 배치, 다기관 환자 이송 조정, 국제 공급망 차질 대응, 대규모 소프트웨어 장애, 환경영향평가 통합, 복지정책 대안 검토, 복합건설 공정 조정, 다논문 연구근거 종합, 장기 법률사건 기록 통합
- validation 신규 객체·상황 bank: 극지 탐사대 운영기록, 오페라 제작 전과정, 위성 발사 임무기록, 다년 고고학 발굴기록, 항만 준설 영향 검토
- pilot 예약: `S6-A01-T-001`, `S6-A03-T-001`, `S6-A06-T-001`, `S6-A01-V-001`
- contingency domain bank: 산악 철도 대수선, 백신 공급 캠페인, 해상풍력 건설, 국가기록물 디지털화, 유역 가뭄 공동대응
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 410 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 35. Stage 7 — 지시 수행·대화·실전 사용

명령 이해, 출력 형식 준수, 다턴 대화, 도구·프로토콜 확장, 안전과 불확실성 처리, 실전 task 수행을 다룬다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 지시·의도 해석 / `instruction_intent` | 20% | 600,000 | 45/5 | `instruction_intent_packet` | `S7-IIH` / `S7-IIV` | 명시 요구, 범위, 금지, 우선순위와 완료 조건을 정확히 추출한다. | 부수 설명을 명령으로 오독, 금지 누락, 범위 확대 |
| 2 / 2 | 출력 형식 준수 / `output_format` | 20% | 600,000 | 45/5 | `output_format_packet` | `S7-OFH` / `S7-OFV` | 스키마·순서·길이·언어·금지 형식을 의미 손실 없이 지킨다. | 내용은 맞지만 형식 위반, 필드 추가, 순서·개수 오독 |
| 3 / 3 | 다턴 대화 수행 / `multiturn_dialogue` | 16% | 480,000 | 36/4 | `multiturn_dialogue_packet` | `S7-MDH` / `S7-MDV` | 이전 결정·수정·미해결 질문·사용자 선호를 유지해 후속 행동을 정한다. | 취소된 요구 재사용, 새 지시로 전체 맥락 삭제, 확인 중복 |
| 4 / 4 | 도구·프로토콜 / `tool_protocol` | 16% | 480,000 | 36/4 | `tool_protocol_packet` | `S7-TPH` / `S7-TPV` | 도구 선택, 입력 검증, 결과 해석, 오류·재시도·권한 경계를 준수한다. | 도구 결과 조작, 실패를 성공으로 보고, 권한 없는 실행 |
| 5 / 5 | 안전·불확실성 처리 / `safety_uncertainty` | 16% | 480,000 | 36/4 | `safety_uncertainty_packet` | `S7-SUH` / `S7-SUV` | 위험도, 권한, 가역성, 불확실성에 따라 질문·보류·거절·안전 대안을 선택한다. | 불확실한 고위험 행동 실행, 저위험 과업 과잉 거절, 권한 추정 |
| 6 / 6 | 실전 task 완결 / `practical_task` | 12% | 360,000 | 27/3 | `practical_task_packet` | `S7-PTH` / `S7-PTV` | 계획·실행·검증·보고를 연결해 실제 산출물의 완료 상태를 판정한다. | 준비를 완료로 보고, 검증 생략, 사용자에게 결과 위치 미고지 |

- train 객체·상황 bank: 보고서 형식 변환, 표 데이터 정제, 회의 일정 조율, 소프트웨어 변경 검토, 창고 재고 조정, 여행 예약 변경, 실험실 안전 절차 수행, 고객 문의 처리, 건물 대피 훈련
- validation 신규 객체·상황 bank: 유물 보존 점검표 실행, 스포츠 대회 운영 프로토콜, 지역 라디오 방송 편성, 임시진료소 접수 흐름, 천문관 공개관측 행사
- pilot 예약: `S7-A01-T-001`, `S7-A03-T-001`, `S7-A06-T-001`, `S7-A01-V-001`
- contingency domain bank: 법원 서류 제출, 학교급식 알레르기 대응, 공유자전거 정비, 전시회 발권 운영, 해안 정화 자원봉사
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 470 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 36. Stage 8 — 평가·비판·검증·수정

Stage7의 실행 결과를 근거 품질, 오류, 논증, 검증, 수정과 확신 보정의 관점에서 독립 평가한다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 근거 품질 / `evidence_quality` | 20% | 600,000 | 45/5 | `evidence_quality_packet` | `S8-EQH` / `S8-EQV` | 주장별 근거의 직접성·독립성·범위·시점·측정 한계를 평가한다. | 근거 수를 품질로 대체, 인용 존재만으로 주장 확정, 간접 근거 과장 |
| 2 / 2 | 오류 탐지 / `error_detection` | 20% | 600,000 | 45/5 | `error_detection_packet` | `S8-EDH` / `S8-EDV` | 사실·논리·계산·범위·일관성 오류를 유형과 영향으로 식별한다. | 이견을 오류로 취급, 표면 오탈자만 고침, 연쇄 영향 누락 |
| 3 / 3 | 논증 비판 / `argument_critique` | 16% | 480,000 | 36/4 | `argument_critique_packet` | `S8-ACH` / `S8-ACV` | 주장·전제·근거·보증·반론 구조를 복원하고 가장 약한 연결을 평가한다. | 결론 불호를 논증 실패로 대체, 숨은 전제 방치, 반론 왜곡 |
| 4 / 4 | 검증·재현 / `verification_validation` | 16% | 480,000 | 36/4 | `verification_validation_packet` | `S8-VRH` / `S8-VRV` | 명세·테스트·독립 계산·교차 확인으로 주장을 재현 가능하게 검증한다. | 테스트 통과를 전체 정당성으로 확대, 같은 계산을 독립 검증으로 오인 |
| 5 / 5 | 수정·교정 / `revision_correction` | 16% | 480,000 | 36/4 | `revision_correction_packet` | `S8-RCH` / `S8-RCV` | 오류 원인과 영향 범위를 최소 수정으로 교정하고 재검증한다. | 증상만 덮기, 정답까지 변경, 수정 뒤 회귀검사 누락 |
| 6 / 6 | 확신 보정·유보 / `calibration_abstention` | 12% | 360,000 | 27/3 | `calibration_abstention_packet` | `S8-CAH` / `S8-CAV` | 증거 강도에 맞춰 확신·조건부 답·추가 확인·판단 유보를 선택한다. | 근거 없는 단정, 모든 불확실성에 회피, 정확도와 확신 혼동 |

- train 객체·상황 bank: 과학 실험 보고서, 공공 데이터 대시보드, 정책 효과 메모, 소프트웨어 변경안, 탐사보도 기사, 설비 고장 진단서, 언어모델 응답, 법률 논증서, 교육 평가 문항
- validation 신규 객체·상황 bank: 박물관 소장 이력 보고, 야생동물 카메라 판독, 오케스트라 리허설 기록, 지질도 해석 보고, 식품 관능평가 결과
- pilot 예약: `S8-A01-T-001`, `S8-A03-T-001`, `S8-A06-T-001`, `S8-A01-V-001`
- contingency domain bank: 임상지침 요약, 특허 신규성 검토, 교량 안전점검, 금융 공시 검토, 번역 품질 검토
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 500 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 37. Stage 9 — 연구·도구 오케스트레이션·지속 워크플로

다중 출처 조사, 여러 도구, 장기 상태, 협업 인계, 모니터링과 출처 감사를 하나의 지속 workflow로 운영한다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 조사·종합 / `research_synthesis` | 20% | 600,000 | 45/5 | `research_synthesis_packet` | `S9-RSH` / `S9-RSV` | 질문을 검색 가능한 하위 문제로 나누고 다중 출처를 비교해 출처 있는 종합을 만든다. | 검색 결과 나열, 출처 충돌 은폐, 인용과 추론 혼합 |
| 2 / 2 | 도구 오케스트레이션 / `tool_orchestration` | 20% | 600,000 | 45/5 | `tool_orchestration_packet` | `S9-TOH` / `S9-TOV` | 여러 도구의 입력·출력·의존성·실패를 계획하고 결과를 연결한다. | 도구 순서 역전, 중간 결과 미검증, 실패 출력 재사용 |
| 3 / 3 | 워크플로 상태 지속 / `workflow_state` | 16% | 480,000 | 36/4 | `workflow_state_packet` | `S9-WSH` / `S9-WSV` | 장기 작업의 완료·진행·대기·차단 상태와 산출물 버전을 보존한다. | 계획을 완료로 표시, 중단 뒤 중복 실행, 오래된 산출물 사용 |
| 4 / 4 | 협업·인계 / `collaboration_handoff` | 16% | 480,000 | 36/4 | `collaboration_handoff_packet` | `S9-CHH` / `S9-CHV` | 역할·권한·결정·미해결 항목·산출물을 다른 작업자에게 무손실 인계한다. | 책임 불명, 결정과 제안 혼동, 미실행 항목 누락 |
| 5 / 5 | 모니터링·적응 / `monitoring_adaptation` | 16% | 480,000 | 36/4 | `monitoring_adaptation_packet` | `S9-MAH` / `S9-MAV` | 관측 지표와 임계 조건을 바탕으로 기다림·알림·재계획·중단을 선택한다. | 변화 없는 상태를 실패로 오인, 과도한 polling, 기준 없는 재계획 |
| 6 / 6 | 출처·감사 가능성 / `provenance_audit` | 12% | 360,000 | 27/3 | `provenance_audit_packet` | `S9-PAH` / `S9-PAV` | 데이터·결정·변경·도구 결과의 계보와 재현 증거를 유지한다. | 출처 누락, 생성물과 원본 혼동, 실행하지 않은 검증 보고 |

- train 객체·상황 bank: 학술 조사 프로젝트, 소프트웨어 배포 프로그램, 하천 현장조사 캠페인, 공공조달 절차, 보안사고 대응, 다매체 콘텐츠 제작, 내부통제 감사, 지역복지 프로그램, 데이터센터 이전
- validation 신규 객체·상황 bank: 남극 보급 운영, 독립영화제 운영, 습지 복원 협업, 전파망원경 유지보수, 난민지원 거점 운영
- pilot 예약: `S9-A01-T-001`, `S9-A03-T-001`, `S9-A06-T-001`, `S9-A01-V-001`
- contingency domain bank: 선거 관찰 임무, 오픈소스 학술대회, 산호 양묘장 운영, 비상 통신망 전개, 공공 지도 갱신
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 510 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 38. Stage 10 — 통합 전문 수행·장기 안전 자율성

도메인 지식, 추론, 도구, 협업과 검증을 장기 목표 아래 통합하면서 적대적 조건과 안전 경계를 관리한다.

| 교육# / slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 전문 지식 통합 / `expert_integration` | 20% | 600,000 | 45/5 | `expert_integration_packet` | `S10-EIH` / `S10-EIV` | 여러 전문 영역의 정의·증거·제약·실행 기준을 충돌 없이 통합한다. | 한 도메인 기준을 타 도메인에 강제, 전문 용어 동형이의 혼합 |
| 2 / 2 | 교차 도메인 종합 / `crossdomain_synthesis` | 20% | 600,000 | 45/5 | `crossdomain_synthesis_packet` | `S10-CSH` / `S10-CSV` | 서로 다른 도메인의 구조를 대응시켜 새 해결안을 만들고 전이 한계를 검증한다. | 표면 비유를 해법으로 채택, 도메인 고유 위험 누락, 단위 불일치 |
| 3 / 3 | 장기 계획·자율 수행 / `long_horizon` | 16% | 480,000 | 36/4 | `long_horizon_packet` | `S10-LHH` / `S10-LHV` | 장기 목표를 단계·검증·승인·재계획으로 운영하며 상태를 지속한다. | 단기 성과로 최종 목표 완료 처리, 목표 표류, 승인 경계 초과 |
| 4 / 4 | 적대적·비정상 조건 강건성 / `adversarial_robustness` | 16% | 480,000 | 36/4 | `adversarial_robustness_packet` | `S10-ARH` / `S10-ARV` | 오염 정보, 기만, 분포 변화, 복합 실패 아래 핵심 불변조건을 지킨다. | 권위 있는 형식의 거짓 수용, 단일 신호 의존, 공격과 단순 오류 혼동 |
| 5 / 5 | 안전 자율성 / `safe_autonomy` | 16% | 480,000 | 36/4 | `safe_autonomy_packet` | `S10-SAH` / `S10-SAV` | 위험·권한·가역성·감독 가능성에 맞춰 자율 실행과 인간 승인을 배분한다. | 목표를 이유로 권한 확대, 불가역 행동 무승인 실행, 안전과 성과 상충 은폐 |
| 6 / 6 | 메타인지·자기통제 / `metacognitive_control` | 12% | 360,000 | 27/3 | `metacognitive_control_packet` | `S10-MCH` / `S10-MCV` | 자신의 지식·계획·검증 한계를 점검하고 추가 탐색·수정·유보를 선택한다. | 자기평가를 증거로 간주, 동일 방법 반복, 비용 없는 무한 검증 |

- train 객체·상황 bank: 연안 기후적응 전략, 지역 공중보건 계획, 스마트도시 전환, 자율실험실 연구, 분산에너지 전환, 국가 사이버방어, 성인교육 체계개편, 심우주 탐사 임무, 대지진 장기복구
- validation 신규 객체·상황 bank: 문화재 반환 협상, 해양 탄소 관측망, 달 표면 거주기지, 감염병 기록 아카이브, 국제하천 공동관리
- pilot 예약: `S10-A01-T-001`, `S10-A03-T-001`, `S10-A06-T-001`, `S10-A01-V-001`
- contingency domain bank: 인공지능 보건 거버넌스, 초국경 식량안보, 궤도 잔해 완화, 초대형 가뭄 적응, 디지털 공공인프라
- 상태: primary 예약 기준 pilot 4 files·600 records 완료·독립 의미 감사 PASS. 현행 승인 총량은 490 files이며 중앙 schema 2.0 예약 완료; 직접 작성 생성 진행률은 §40.7과 작업원장을 따른다.

## 39. Stage 2~10 concept-family 중앙 원장과 준비 폴더

정확한 150-record family 이름·split·version·filename·ID 범위는 `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json`을 본 설계서의 기계 판독 부속 원장으로 사용한다. 요약표만으로 family를 다시 선정하지 않는다.

| 항목 | 실측 |
|---|---:|
| 전체 reservation | 4,370 |
| train / validation | 3,933 / 437 |
| origin — primary / contingency / new | 2,250 / 225 / 1,895 |
| 전체 concrete records | 655,500 |
| Stage별 승인 files | 480 / 470 / 440 / 600 / 410 / 470 / 500 / 510 / 490 |
| reservation ID 중복 | 0 |
| filename 중복 | 0 |
| exact·정규화 family 중복 | 0 |
| origin 간 정규화 family 중복 | 0 |
| Stage별 train–validation domain overlap | 0 |
| relation focus의 통제 어휘 밖 값 | 0 |
| Stage2 legacy filename 충돌 | 0 |
| 현행 corpus JSON | 74 files / 11,100 records |
| 현행 canonical source | 122 files / 18,300 rows; 완료 쌍 74 + 완결 source-only 48 |
| 보존 pilot corpus/source | 36 / 36 files |
| pilot 사용 primary reservation | 36 |

준비 기준선 중앙 원장 SHA-256은 `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99`였고, 승인 revision 현행 SHA-256은 `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`이다. 세부 사람이 읽는 설계·검토본은 `TinyLM_Stage2_Stage10_Curriculum_and_Family_Reservation_Draft.md`에 보존한다.

TinyDataset 최상위에 `stage2_highdensity_dataset/`부터 `stage10_highdensity_dataset/`까지 만들었다. 각 폴더는 `train/`, `val/`, `sources/train/`, `sources/val/`, `tools/`, `audit_reports/machine/`, `audit_reports/archive/`, `README.md`, `PREPARATION_MANIFEST.json`을 가진다. 9개 manifest는 schema 2.0, status `ACTUAL_3M_FAMILY_RESERVATIONS_AUTHORIZED`로 revision했고 중앙 원장의 해당 Stage exact projection과 현행 중앙 SHA를 보존한다. 각 Stage의 pilot JSON 4개와 canonical source 4개는 그대로이며 Stage2에 직접 작성 v02~v39 서른여덟 쌍과 v40~v87 완결 source-only 48개를 추가했다.

중앙 원장이나 manifest의 family는 별도 사용자 승인 없이 삭제·재배치·재사용하지 않는다. contingency 225개는 이미 승인 배치·활성화됐으므로 primary·new와 같은 예약 불변조건을 적용한다.

준비 상태의 기계 감사 정본은 `audit_reports/machine/TinyLM_Stage2_10_Preparation_Audit_2026-09-01.json`이며 verdict는 `PASS`다. Identity 통제 필드 추가까지 끝난 뒤 저밀도 31파일, 요청 범위 밖 Stage1 고밀도 JSON 214파일, Identity 기존 필드 투영 41파일, Identity validation 4파일과 Stage2~10 무코퍼스 상태를 다시 대조한 당시 보호 감사도 `audit_reports/machine/TinyLM_Stage2_10_Identity_Final_Protection_Comparison_2026-09-01.json`에 역사적 `PASS`로 보존한다. Pilot 작업의 현행 보호·품질 판정은 §40의 2026-09-02 통합 감사를 우선한다.

## 40. Stage 2~10 tokenizer pilot 확정·실측 3M 승인·실행 원장

### 40.1 실생성 범위와 감사 판정

2026-09-02 각 Stage의 A01·A03·A06 train v01과 A01 validation v01을 직접 작성했다. 합계 36 files·5,400 records(train 4,050, validation 1,350)는 배분 결정을 위한 pilot으로 보존한다. 후속 승인 뒤 Stage2 A01 train v01~v87, A02 train v01~v86, A03 train v01~v69를 각각 영역 단위로 완결·감사·포장했다. 2026-09-09 기준 이 세 영역은 242 files·36,300 train records이며 모두 통합 감사 PASS다.

- JSON·UTF-8·schema·metadata·ID·source 대응·relations·exact duplicate 오류: 0
- 중앙 예약 row·area와 파일 metadata exact 대응: 36/36; 5,400 records의 type·split·연속 ID mismatch: 0
- validation: `unseen_relation: true` 162/1,350 = 12.00%; true set의 train 관측 0, false set의 train 미관측 0, validation 개별 label의 train 미관측 0
- true 위치: 최대 연속 3, 각 30-record 구간 최소 2
- 내부·Stage1 고밀도 교차 반복 5어절: 0/0; 반복 4어절 문장 도입부: 0
- 문자 3~5-gram TF-IDF 최대 cosine: pilot 내부 0.340176, Stage1 고밀도 교차 0.220597; 검토선 0.72 이상 0/0
- primary concept 직결 조사 후보: 0
- 문서 갱신 직전 보호 기준선: 저밀도·Stage1 고밀도·기존 scaffold·중앙 통제 문서 371/371 일치, 변경·누락 0/0. 이후 본 설계서만 의도적으로 갱신했고 pilot JSON/source 72개는 별도 post-check에서 72/72 일치했다.

독립 의미 감사는 작성자와 다른 검토자가 Stage2~4, Stage5~7, Stage8~10 세 구간으로 수행했다. 각 구간의 고정 층화 표본, validation true 전수, 희소 relation, 기계 유사도 상위쌍과 모든 교정 ID를 재판독했으며 세 보고서 모두 최종 `PASS`, 미해결 지적 0, 독립 감사자의 corpus/source/JSON 수정 0이다.

### 40.2 relations 분포와 `other`

| relation | 횟수 |
|---|---:|
| `is_a` | 3 |
| `subclass_of` | 7 |
| `part_of` | 502 |
| `classification` | 1,620 |
| `boundary` | 3,453 |
| `contrast` | 460 |
| `comparison` | 1,142 |
| `function` | 1,187 |
| `role` | 1,062 |
| `process` | 2,291 |
| `state` | 3,508 |
| `attribute` | 1,600 |
| `other` | 784 |

`other` 상위 유형 5개와 대표 concept은 일정 불확실성 3회 — `복구 예정 시각 불확실` (`S6-LCH-00094`), 관측 결측 3회 — `기상 센서의 관측 공백` (`S6-CSH-00070`), 시간정보 결측 3회 — `현장 사진의 촬영 시각 미상` (`S6-UMH-00130`), 관측 공백 3회 — `생태 조사 야간 종 검출 공백` (`S8-EQH-00036`), 희귀 단일 사례 2회 — `한 회차 압력 급락 예외` (`S2-CSH-00150`)다. Stage별 13개 분포와 Stage별 `other` 상위 5유형은 통합 감사 정본에 둔다.

### 40.3 실제 tokenizer 실측과 승인 배분

기준 tokenizer는 `tok-ko-en-32768.json`이며 record마다 학습 경로와 같은 EOS 1개를 더했다. 전체 pilot은 224,631 tokens, 평균 41.598333 tokens/record다. 민감도 참고값은 `tok-ko-edu-en-32768.json` 210,399, `tok-ko-32768.json` 205,018 tokens다. 수정 금지 Stage1 고밀도 train+validation 255 files·38,200 records는 같은 기준으로 1,479,956 tokens, 평균 38.742304다.

| Stage | pilot 평균 token/record | 승인 files | train/val | records | 투영 tokens | primary 250 대비 증보 | contingency 25 이후 신규 family | pilot 제외 생성 대기 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 41.625000 | 480 | 432/48 | 72,000 | 2,997,000 | 230 | 205 | 476 |
| 3 | 42.883333 | 470 | 423/47 | 70,500 | 3,023,275 | 220 | 195 | 466 |
| 4 | 45.316667 | 440 | 396/44 | 66,000 | 2,990,900 | 190 | 165 | 436 |
| 5 | 33.183333 | 600 | 540/60 | 90,000 | 2,986,500 | 350 | 325 | 596 |
| 6 | 48.551667 | 410 | 369/41 | 61,500 | 2,985,928 | 160 | 135 | 406 |
| 7 | 42.600000 | 470 | 423/47 | 70,500 | 3,003,300 | 220 | 195 | 466 |
| 8 | 39.616667 | 500 | 450/50 | 75,000 | 2,971,250 | 250 | 225 | 496 |
| 9 | 39.548333 | 510 | 459/51 | 76,500 | 3,025,447 | 260 | 235 | 506 |
| 10 | 41.060000 | 490 | 441/49 | 73,500 | 3,017,910 | 240 | 215 | 486 |
| **합계** | — | **4,370** | **3,933/437** | **655,500** | **27,001,510** | **2,120** | **1,895** | **4,334** |

기존 250 files는 Stage별 약 1.24M~1.82M tokenizer tokens에 해당하므로 실제 3M이 아니다. 250 files를 유지하면서 record 길이만 늘리려면 Stage별 1.65~2.41배가 필요해 직접성·고밀도 문체를 해칠 위험이 있다.

2026-09-02 사용자는 위 **실제 tokenizer 기준 Stage별 약 3M안**을 먼저 승인했고, 이어서 Stage5~7 gate 수정·family 완전 예약·중앙 원장/manifest revision·남은 4,334 files 실제 생성을 명시적으로 승인했다. Stage1 규모 비교안은 비채택 참고안으로만 남고 향후 총량 계산에 섞지 않는다. 직접 생성 권한은 Guide §10의 자동 의미 생성 금지를 완화하지 않는다.

### 40.4 증보 원칙과 승인 경계

- `primary 대비 증보`는 승인 총 files에서 현행 primary 250을 뺀 값이다.
- 비활성 contingency 25개/Stage, 합계 225개는 의미 적합성을 재검토해 54개 세부영역과 train/validation에 배치하고 area·split·ID·version·filename을 확정했다.
- 신규 family 1,895개는 정확한 이름·도메인·세부 `semantic_axis`를 선정했다. 중앙 원장 전체 4,370행에서 exact·정규화 family 중복, filename·ID range·concrete ID 중복은 모두 0이다.
- §40.5의 증보 version 범위는 중앙 schema 2.0 원장과 Stage별 manifest의 실제 예약으로 활성화했다. 중앙 원장 SHA-256은 `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`이다.
- version은 v01부터 연속하며 v01~v99는 두 자리 0-padding, 100 이상은 v100처럼 표기한다. Stage5 A01·A02의 승인 train 상한 v108 때문에 이 규칙을 명시한다.
- Stage5~7 builder/auditor 수정과 12 pilot files·1,800 records 재감사, 중앙 원장/9개 manifest revision과 family 독립성 감사를 완료했다.
- corpus는 전체 train을 Stage2→10 순으로 직접 작성하고 validation을 같은 순서로 생성한다. 2026-09-02 추가 지침부터 파일별 반복 감사·수정 대신 **한 Stage의 교육영역 source 전체를 완성한 뒤** token·중복·유사도·조사 batch 감사와 수정을 하고 corpus를 일괄 포장한다. 2026-09-08 현재 Stage2 A01 train 87개와 A02 train 86개는 영역 감사와 포장을 모두 통과했고, 다음 직접 작성점은 기존 A03 v01 pilot을 보존한 `S2-A03-T-002`다.
- 저밀도, held-out/evaluation, Stage1 수정 금지 corpus와 legacy `stage2_(2)attribute_high_density_*`는 계속 source·생성·재직렬화 범위에서 제외한다.

### 40.5 Stage별·세부영역별 승인 총량과 증보 계획

`기존 T/V`는 시작 primary 예약, `승인 T/V`는 실측 3M안의 최종 총량, `증보 T/V`는 두 값의 차이다. `pilot 완료`는 승인 전 존재하던 JSON이며 `생성 대기`는 승인 총량에서 pilot을 뺀 시작 수량이다. version 범위는 중앙 schema 2.0 원장에서 실제 filename·ID range로 활성화됐으며, 현행 잔여 수는 작업원장을 우선한다. version은 영역·split별 로컬 번호이고 전역 식별 키는 `(stage, area_slug, split, version)`이므로, 서로 다른 영역이나 train/validation 사이에서 같은 version 번호를 쓰는 것은 정상이다.

#### Stage 2 — 복합 관계·의존·인과·조건 구조

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 원인 구조 | `causal_structure` | 45/5 | 87/9 | +42/+4 | v46~v87 / v06~v09 | 1/1 | 86/8 |
| A02 조건·의존 구조 | `conditional_dependency` | 45/5 | 86/9 | +41/+4 | v46~v86 / v06~v09 | 0/0 | 86/9 |
| A03 시간 순서·간격 | `temporal_order` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 1/0 | 68/8 |
| A04 상태 전이·동역학 | `state_transition` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 0/0 | 69/8 |
| A05 가능성·양상 | `modality_possibility` | 36/4 | 69/8 | +33/+4 | v37~v69 / v05~v08 | 0/0 | 69/8 |
| A06 다중 관계 조합 | `relational_composition` | 27/3 | 52/6 | +25/+3 | v28~v52 / v04~v06 | 1/0 | 51/6 |

#### Stage 3 — 절차·행동·계획·문제 해결

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 목표·행동 연결 | `goal_action` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 1/1 | 83/8 |
| A02 절차·순서 | `procedure_sequence` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 0/0 | 84/9 |
| A03 계획 분해 | `planning_decomposition` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 1/0 | 67/8 |
| A04 제약·자원 | `constraint_resource` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 0/0 | 68/8 |
| A05 선택·우선순위 | `decision_priority` | 36/4 | 68/7 | +32/+3 | v37~v68 / v05~v07 | 0/0 | 68/7 |
| A06 실행 감시·실패 복구 | `execution_recovery` | 27/3 | 51/6 | +24/+3 | v28~v51 / v04~v06 | 1/0 | 50/6 |

#### Stage 4 — 문맥·담화·지시·대화

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 담화 지시·참조 | `discourse_reference` | 45/5 | 79/9 | +34/+4 | v46~v79 / v06~v09 | 1/1 | 78/8 |
| A02 생략·공동지시 | `ellipsis_coreference` | 45/5 | 79/9 | +34/+4 | v46~v79 / v06~v09 | 0/0 | 79/9 |
| A03 대화 상태 | `dialogue_state` | 36/4 | 64/7 | +28/+3 | v37~v64 / v05~v07 | 1/0 | 63/7 |
| A04 질문–응답 적합성 | `question_answer` | 36/4 | 63/7 | +27/+3 | v37~v63 / v05~v07 | 0/0 | 63/7 |
| A05 화행·대화 행위 | `speech_act_pragmatics` | 36/4 | 63/7 | +27/+3 | v37~v63 / v05~v07 | 0/0 | 63/7 |
| A06 함축·맥락 의존 | `implicature_context` | 27/3 | 48/5 | +21/+2 | v28~v48 / v04~v05 | 1/0 | 47/5 |

#### Stage 5 — 일반화·추론·전이

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 귀납 일반화 | `induction` | 45/5 | 108/12 | +63/+7 | v46~v108 / v06~v12 | 1/1 | 107/11 |
| A02 연역 추론 | `deduction` | 45/5 | 108/12 | +63/+7 | v46~v108 / v06~v12 | 0/0 | 108/12 |
| A03 반례 기반 일반화 | `counterexample_generalization` | 36/4 | 87/10 | +51/+6 | v37~v87 / v05~v10 | 1/0 | 86/10 |
| A04 새 조합 일반화 | `compositional_novelty` | 36/4 | 86/10 | +50/+6 | v37~v86 / v05~v10 | 0/0 | 86/10 |
| A05 유추 전이 | `analogical_transfer` | 36/4 | 86/9 | +50/+5 | v37~v86 / v05~v09 | 0/0 | 86/9 |
| A06 도메인 구조 전이 | `structural_transfer` | 27/3 | 65/7 | +38/+4 | v28~v65 / v04~v07 | 1/0 | 64/7 |

#### Stage 6 — 지식 통합·장문맥·복합 문제

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 장문맥 유지 | `long_context` | 45/5 | 74/8 | +29/+3 | v46~v74 / v06~v08 | 1/1 | 73/7 |
| A02 다단계 추론 | `multihop_inference` | 45/5 | 74/8 | +29/+3 | v46~v74 / v06~v08 | 0/0 | 74/8 |
| A03 복합 제약 만족 | `constraint_satisfaction` | 36/4 | 59/7 | +23/+3 | v37~v59 / v05~v07 | 1/0 | 58/7 |
| A04 다중 목표·절충 | `multiobjective_tradeoff` | 36/4 | 59/7 | +23/+3 | v37~v59 / v05~v07 | 0/0 | 59/7 |
| A05 다중 출처 통합 | `multisource_integration` | 36/4 | 59/6 | +23/+2 | v37~v59 / v05~v06 | 0/0 | 59/6 |
| A06 불확실성 관리 | `uncertainty_management` | 27/3 | 44/5 | +17/+2 | v28~v44 / v04~v05 | 1/0 | 43/5 |

#### Stage 7 — 지시 수행·대화·실전 사용

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 지시·의도 해석 | `instruction_intent` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 1/1 | 83/8 |
| A02 출력 형식 준수 | `output_format` | 45/5 | 84/9 | +39/+4 | v46~v84 / v06~v09 | 0/0 | 84/9 |
| A03 다턴 대화 수행 | `multiturn_dialogue` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 1/0 | 67/8 |
| A04 도구·프로토콜 | `tool_protocol` | 36/4 | 68/8 | +32/+4 | v37~v68 / v05~v08 | 0/0 | 68/8 |
| A05 안전·불확실성 처리 | `safety_uncertainty` | 36/4 | 68/7 | +32/+3 | v37~v68 / v05~v07 | 0/0 | 68/7 |
| A06 실전 task 완결 | `practical_task` | 27/3 | 51/6 | +24/+3 | v28~v51 / v04~v06 | 1/0 | 50/6 |

#### Stage 8 — 평가·비판·검증·수정

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 근거 품질 | `evidence_quality` | 45/5 | 90/10 | +45/+5 | v46~v90 / v06~v10 | 1/1 | 89/9 |
| A02 오류 탐지 | `error_detection` | 45/5 | 90/10 | +45/+5 | v46~v90 / v06~v10 | 0/0 | 90/10 |
| A03 논증 비판 | `argument_critique` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 1/0 | 71/8 |
| A04 검증·재현 | `verification_validation` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 0/0 | 72/8 |
| A05 수정·교정 | `revision_correction` | 36/4 | 72/8 | +36/+4 | v37~v72 / v05~v08 | 0/0 | 72/8 |
| A06 확신 보정·유보 | `calibration_abstention` | 27/3 | 54/6 | +27/+3 | v28~v54 / v04~v06 | 1/0 | 53/6 |

#### Stage 9 — 연구·도구 오케스트레이션·지속 워크플로

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 조사·종합 | `research_synthesis` | 45/5 | 92/11 | +47/+6 | v46~v92 / v06~v11 | 1/1 | 91/10 |
| A02 도구 오케스트레이션 | `tool_orchestration` | 45/5 | 92/10 | +47/+5 | v46~v92 / v06~v10 | 0/0 | 92/10 |
| A03 워크플로 상태 지속 | `workflow_state` | 36/4 | 74/8 | +38/+4 | v37~v74 / v05~v08 | 1/0 | 73/8 |
| A04 협업·인계 | `collaboration_handoff` | 36/4 | 73/8 | +37/+4 | v37~v73 / v05~v08 | 0/0 | 73/8 |
| A05 모니터링·적응 | `monitoring_adaptation` | 36/4 | 73/8 | +37/+4 | v37~v73 / v05~v08 | 0/0 | 73/8 |
| A06 출처·감사 가능성 | `provenance_audit` | 27/3 | 55/6 | +28/+3 | v28~v55 / v04~v06 | 1/0 | 54/6 |

#### Stage 10 — 통합 전문 수행·장기 안전 자율성

| 영역 | slug | 기존 T/V | 승인 T/V | 증보 T/V | 증보 version 범위 (train / validation; 영역·split 로컬) | pilot 완료 T/V | 생성 대기 T/V |
|---|---|---:|---:|---:|---|---:|---:|
| A01 전문 지식 통합 | `expert_integration` | 45/5 | 88/10 | +43/+5 | v46~v88 / v06~v10 | 1/1 | 87/9 |
| A02 교차 도메인 종합 | `crossdomain_synthesis` | 45/5 | 88/9 | +43/+4 | v46~v88 / v06~v09 | 0/0 | 88/9 |
| A03 장기 계획·자율 수행 | `long_horizon` | 36/4 | 71/8 | +35/+4 | v37~v71 / v05~v08 | 1/0 | 70/8 |
| A04 적대적·비정상 조건 강건성 | `adversarial_robustness` | 36/4 | 71/8 | +35/+4 | v37~v71 / v05~v08 | 0/0 | 71/8 |
| A05 안전 자율성 | `safe_autonomy` | 36/4 | 70/8 | +34/+4 | v37~v70 / v05~v08 | 0/0 | 70/8 |
| A06 메타인지·자기통제 | `metacognitive_control` | 27/3 | 53/6 | +26/+3 | v28~v53 / v04~v06 | 1/0 | 52/6 |

### 40.6 Stage1 `relations` 필드의 Stage2~10 적용 검토

결론은 **13개 통제 어휘와 `relations` schema를 유지하되, 고차 교육능력 label로 과잉 해석하지 않는 조건부 유지**다. 여기서 유지 대상은 통제 완료된 13개 schema이며, identity legacy의 자유 어휘 원본 `relations` 1,916종을 Stage2~10으로 전파한다는 뜻이 아니다.

| 층 | 담당 정보 | 규칙 |
|---|---|---|
| `relations` | 문장에 실제로 나타난 기초 의미 관계의 비완전 투영 | 기존 13개 중 2~5개, 내부 중복 금지 |
| `type` | Stage2~10의 고차 교육능력 | 54개 `<slug>_packet`으로 인과·조건·계획·담화·검증 등을 구분 |
| `concept_family` | domain과 세부 semantic axis | 한 파일 150 records의 주제 경계이며 text template가 아님 |

따라서 `causal`, `dependency`, `temporal_order`, `evidence` 같은 새 이름을 `relations`에 추가하지 않는다. 해당 능력은 `type`별로 평가한다. 반대로 causal file이라는 이유만으로 `process`, `state`, `boundary`를 억지로 붙이거나 고차 능력을 `other`로 대체하지 않는다. `relations`는 완전한 관계 그래프가 아니며 `relation_focus`는 whitelist·필수 교집합·분포 목표가 아니다.

Pilot 근거는 통제 밖 relation 0, record별 길이·중복 오류 0, 전체 17,619 relation 배정 중 `other` 784회(4.4497%)다. 13개는 전체 pilot에서 모두 관측됐지만 Stage별 0회인 label이 있으며, 이는 의미 차이이므로 강제 보충하지 않는다. validation은 개별 label을 train에서 관측하고 `unseen_relation`을 새 label이 아니라 train 미관측 정렬 relation-set 조합으로 사용한다.

전체 생성 중 다음을 파일 단위·통합 gate로 계속 감사한다.

1. 모든 record의 `type`이 예약 Stage·area packet type과 정확히 일치한다.
2. `relations` 각 값이 text에서 직접 근거를 가지며 13개 중 2~5개다.
3. Stage·area별 관계 분포를 인위적으로 균등화하지 않는다.
4. `other` 의미 유형과 대표 concept을 계속 보고한다.
5. Stage5·6·7의 `tools/build_pilot.py`와 Stage5의 `tools/audit_pilot.py`에 있던 `relations ⊆ relation_focus` 강제를 제거했다. 13개 통제 어휘·2~5개·record 내부 중복 금지·source projection gate는 유지했고, 12 pilot files·1,800 records 재감사 오류 0 및 corpus/source SHA 24/24 일치를 확인했다.
6. 평가 결과는 13개 relation 축과 54개 `type` 축을 분리해 보고한다.

새 `capability` field는 현행 `type`과 중복되므로 추가하지 않는다. downstream loader가 `type`을 보존하지 않는 사실이 확인될 때만 별도 schema 변경안을 사용자 승인 대상으로 올린다.

### 40.7 후속 승인 실행 상태와 재개점

- 중앙 family 원장: schema 2.0, 4,370 reservations, train/validation 3,933/437, 655,500 records
- family origin: primary 2,250, contingency 225, new 1,895
- Stage manifest: 9/9 중앙 원장의 exact Stage projection, revision 감사 23개 검사 오류 0
- 실행 착수 초기 snapshot(2026-09-02): 완료 corpus/source pairs 74/74 files·11,100 records였고, 기존 pilot 36쌍과 직접 작성 신규 `S2-A01-T-002~039` 38쌍으로 구성됐다.
- A01 일괄 감사 전 snapshot(2026-09-03): `S2-A01-T-040~087` source 48개·7,200행이 source-only 상태였으며, 이후 아래의 A01 최종 감사·포장 기록으로 대체됐다.
- 중단·재개 source: `S2-A01-T-051`의 기존 50행을 보존하고 100행을 직접 보충해 150행 완결. source SHA-256 `11adf713d54a596d352f4487cd23b710adfc2d1faad37719e1311bef5be703c6`
- 중단·재개 확정: `S2-A01-T-039`의 기존 98행을 보존하고 52행을 직접 보충해 source/corpus/checkpoint 및 독립 감사를 PASS. source SHA-256 `27d8e23d5e4cd82b66d5907bd223ba7c43f4e605cfa10fc6bb99f7ae6b57e52f`, corpus SHA-256 `949994562255517567f4475500241075e138db70ac4fb7f6933c1344d5d137e6`
- 신규 v02 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 고유사 pair 0, tokenizer 평균 45.206667(+EOS)로 Stage2 gate PASS
- 신규 v03 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 44.006667(+EOS)로 Stage2 gate PASS
- 신규 v04 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 38.853333(+EOS)로 Stage2 gate PASS
- 신규 v05 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 41.966667(+EOS)로 Stage2 gate PASS
- 신규 v06 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 42.706667(+EOS)로 Stage2 gate PASS
- 신규 v07 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 43.240000(+EOS)로 Stage2 gate PASS
- 신규 v08 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 45.240000(+EOS)로 Stage2 gate PASS
- 신규 v09 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 교차 고유사 pair 0, tokenizer 평균 38.633333(+EOS)로 Stage2 gate PASS
- 신규 v10 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 train 교차 고유사 pair 0, tokenizer 평균 42.106667(+EOS)로 Stage2 gate PASS
- 신규 v11 감사: relations 통제 밖 0, record당 2~5개 위반 0, exact/normalized 중복 0, 교차 5-word n-gram 반복 0, 내부·기존 Stage2 train 교차 고유사 pair 0, tokenizer 평균 45.386667(+EOS)로 Stage2 gate PASS
- 신규 v12 감사: 초기 token 상한 초과와 누적 5-word n-gram 반복 1종을 직접 수정해 최종 0건, relations·중복·유사도·review debt 오류 0, tokenizer 평균 45.320000(+EOS)로 Stage2 gate PASS
- 신규 v13 감사: 초기 누적 5-word n-gram 반복 1종을 직접 수정해 최종 0건, relations·중복·유사도·review debt 오류 0, tokenizer 평균 44.913333(+EOS)로 Stage2 gate PASS
- 신규 v14 감사: relations 통제 밖·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, tokenizer 평균 44.800000(+EOS)로 Stage2 gate PASS
- 신규 v15 감사: 최초 tokenizer 평균 47.553333 상한 초과와 영문·숫자 말미 primary 조사 6건을 직접 수정했고, 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.220000(+EOS)로 Stage2 gate PASS
- 신규 v16 감사: 파일 내부 5-word 반복 1종과 v11 교차 열거 반복 4종을 직접 재서술해 최종 0건, relations·중복·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 40.033333(+EOS)로 Stage2 gate PASS
- 신규 v17 감사: 파일 내부·누적 5-word 반복 각 1종을 직접 재서술해 최종 0건, relations·중복·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.733333(+EOS)로 Stage2 gate PASS
- 신규 v18 감사: v13과 동일한 primary 1건 및 tokenizer 최초 평균 46.880000 상한 초과를 직접 수정했고, 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.520000(+EOS)로 Stage2 gate PASS
- 신규 v19 감사: primary literal 누락 71건과 v09 교차 primary 1건을 직접 수정했고, 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 38.600000(+EOS)로 Stage2 gate PASS
- 신규 v20 감사: 171행 직접 원고에서 중복 성격 후행 21행을 제외해 150행을 확정하고 내부 5-word 반복 1종을 직접 수정했으며, 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 40.640000(+EOS)로 Stage2 gate PASS
- 신규 v21 감사: 162행 직접 원고에서 후행 보충 후보 12행을 제외해 150행을 확정하고 내부 5-word 반복 2종을 직접 수정했으며, 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 43.000000(+EOS)로 Stage2 gate PASS
- 신규 v22 감사: 최초 150행 source가 구조·tokenizer 계약을 통과했고 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 43.380000(+EOS)로 Stage2 gate PASS
- 신규 v23 감사: 최초 150행 source가 구조·tokenizer 계약을 통과했고 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 44.500000(+EOS)로 Stage2 gate PASS
- 신규 v24 감사: 최초 150행 source가 구조·tokenizer 계약을 통과했고 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 42.906667(+EOS)로 Stage2 gate PASS
- 신규 v25 감사: 최초 직접 원고 148행을 source gate가 차단한 뒤 의미축 2개를 직접 보충했고, package 후 내부 5-word 반복 1종을 직접 수정했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 44.340000(+EOS)로 Stage2 gate PASS
- 신규 v26 감사: 156개 직접 후보 중 중심성이 낮거나 중복 성격인 6개를 제외하고 primary literal 1건과 어색한 primary 1건을 직접 수정했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 44.480000(+EOS)로 Stage2 gate PASS
- 신규 v27 감사: 최초 tokenizer 평균 46.906667 상한 초과를 두 차례 직접 압축해 해결하고, v07과 공유한 5-word n-gram 1종을 직접 재서술했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.500000(+EOS)로 Stage2 gate PASS
- 신규 v28 감사: 최초 직접 원고 148행을 source gate가 차단해 의미축 2개를 직접 보충했고, 완성 원고의 tokenizer 평균 46.973333 상한 초과를 두 차례 직접 압축했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.486667(+EOS)로 Stage2 gate PASS
- 신규 v29 감사: 최초 직접 원고 148행을 source gate가 차단해 의미축 2개를 직접 보충했고, package 후 v12와 공유한 위약검사 5-word n-gram 2종을 직접 재서술했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 41.706667(+EOS)로 Stage2 gate PASS
- 신규 v30 감사: 최초 직접 원고 148행을 source gate가 차단해 의미축 2개를 직접 보충했다. 최초 source·package와 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 40.800000(+EOS)로 Stage2 gate PASS
- 신규 v31 감사: 최초 직접 원고 147행을 source gate가 차단해 의미축 3개를 직접 보충했다. 최초 source·package와 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 38.340000(+EOS)로 Stage2 gate PASS
- 신규 v32 감사: 최초 직접 원고 평균 49.173333의 token 상한 초과를 두 차례 직접 압축했다. 포장 전 source-only와 최종 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.700000(+EOS)로 Stage2 gate PASS
- 신규 v33 감사: 최초 source gate가 primary literal 누락 1건을 차단해 직접 고쳤다. 포장 전 source-only와 최종 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 39.073333(+EOS)로 Stage2 gate PASS
- 신규 v34 감사: 150행 직접 원고가 최초 source gate를 수정 없이 통과했다. 포장 전 source-only와 최종 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 41.953333(+EOS)로 Stage2 gate PASS
- 신규 v35 감사: 포장 전 source-only 감사가 v20 교차 5-word n-gram 1종을 차단해 v35 문장을 직접 재서술했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 43.986667(+EOS)로 Stage2 gate PASS
- 신규 v36 감사: 150행 직접 원고가 최초 source gate를 수정 없이 통과했다. 포장 전 source-only와 최종 전체 감사에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 44.840000(+EOS)로 Stage2 gate PASS
- 신규 v37 감사: 포장 전 source-only 누적 감사가 파일 내부 5-word 반복 1종과 기존 v07·v34 교차 반복 2종을 차단해 v37 문장 3개를 직접 재서술했다. 최종 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.306667(+EOS)로 Stage2 gate PASS
- 신규 v38 감사: 최초 tokenizer 평균 51.013333 상한 초과를 두 차례 직접 압축했고, 포장 전 source-only 누적 감사가 파일 내부·v07 교차 5-word n-gram 각 1종을 차단해 직접 재서술했다. 최종 relations·중복·누적 n-gram·내부 및 기존 Stage2 train 교차 고유사·review debt 오류 0, 평균 45.733333(+EOS)로 Stage2 gate PASS
- 신규 v39 감사: 일시중단 전 source 98행을 보존하고 재개 승인 뒤 52행을 직접 보충했다. 최초 완성 source와 포장 후 file/full audit에서 relations·중복·누적 5-word n-gram·내부 및 기존 Stage2 train 6,000건 교차 고유사·review debt 오류 0, 평균 43.653333(+EOS)로 Stage2 gate PASS
- 자동 semantic-composition 초안: 구조 preflight와 canonical 품질 승인을 분리하며 `manual_semantic_review=false`가 한 건이라도 있으면 canonical write를 차단한다.
- batch 진행물 v40~v50: source 11개·1,650행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. source SHA-256은 v40~v45가 `e0f3edfeebf9f7d19027fa301368ff47ab206a20f8b521cb860fbb6871843639`, `508a1f0b96389ca59a1a24e54559c0a7862fa0f7d075ff8fadb8180f5a8ba62b`, `066119ab81894323fbca8f82ef8f2325edc425bba93b2f282f7037e16fb8e437`, `1ce55695d452e2da7e3f45ad3c1b00469f1b7094e41861268170fe8a782df0ba`, `45eb19c7246aa63dd73e4d71320fdd83af500a185709d5047469b2d01b887932`, `0d9e23c53900488f73f3fc4c3142fa739c98145715b4d4728d4428b54fd9b9d5`, v46~v48이 `43fc6f60257b8d8fce30cc427a2a0458a18a0b71d65c5404b55b8c2add7d0eb5`, `3836f96d5cf05fd7b3308d2f080dc161a9f1d4102eb3e93dbca066e1615b7566`, `7e14ff53c3b3d407be961402a580afac6e1b3be880acd6038f967af85cd065a8`, v49~v50이 `fe82fa73241e8d79a4c21365db31b1f7e49f5655a18154cb3fda284042733fcf`, `f70afd38433fa6a4f5997b91b59429e799faccecfec68cfad47e8354a73ed1b2`다. v40의 전환 직전 예비 token 평균 46.893333(+EOS) 초과는 Stage2 A01 종료 batch 수정 목록에 보존한다.
- batch 진행물 v51: 사용자 중단 시점의 50행을 보존하고 51~150번째 100행을 직접 보충했다. 완성 source의 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류는 0이고 SHA-256은 `11adf713d54a596d352f4487cd23b710adfc2d1faad37719e1311bef5be703c6`이다.
- batch 진행물 v52~v54: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. source SHA-256은 v52 `7958d7d2492c8aab60fddad530d2313689e76929562584d7134ba53454b59897`, v53 `47e11138d8c69c5d4a41b5644cf1704b828eb5043b0c31ae2b34b6d410356dc2`, v54 `c632fdcc21407e949e6ebfdccae13540363e6cc16b0fc97178ab37c10c48053f`다. v54의 최초 149행은 누락 한 행을 직접 보충해 150행으로 맞췄다.
- batch 진행물 v55~v57: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. source SHA-256은 v55 `c42f30c7be0a8b4b2173d955b65a253e77a9e64bee01b1cec3f6bdbdfdf7d01f`, v56 `ca259750951b5b200172825c31196556b8b103af1537ffd4772a2a199de08eea`, v57 `6dae0baccb7ebecd49b00c5402257dd96c99c2e0f997be79877f48613c92ccfa`다.
- batch 진행물 v58~v60: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v58은 실파일 50행을 보존하고 누락 100행을 직접 보충했으며, v60의 primary literal 누락 2건을 직접 수정했다. source SHA-256은 v58 `077b32e1099624d45a6a73a817b8988e05eaa1e81c976c114bea91f60a36d724`, v59 `d987020fc02e9498f651aa2ccf56aa70fa5690fcf8e91ff38763078c86804d92`, v60 `7d3e66a371a8a24a2c197dde23da81d4a8c0c92cdeb9c74772a1a1de1e97b509`다.
- batch 진행물 v61~v63: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v61은 149→150행, v63은 148→150행으로 보충했고 v62는 151→150행으로 축소했다. source SHA-256은 v61 `cc8dc796e77144514ec1709fea3404057593aa8572681f42b7e35a8a219b5f2c`, v62 `d06564e79c83f86462b28cf54eb5983e18eac33f6dbdf4ae0bc928969f229990`, v63 `74475c90f2ce75bc136c4db65102d92ce014b7da2883335fb736f12a03e2e555`다.
- batch 진행물 v64~v66: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v64는 중복어 오탈자 수정과 149→150행 보충, v65는 148→150행 보충을 거쳤고 v66은 최초 검사에서 통과했다. source SHA-256은 v64 `bcf6c8833a07d38c8103280526e1f8f6e2ae4ea63e08ea698ff1b9d5b9a93afe`, v65 `9f8ccbeb0b56fcb5f0673a3f796e22946e0317ec212ad217ff8035f939e0e90d`, v66 `89926e81e0f33375ae0b2192af6006e368dcbf164def6afb979aa5ead8aa1967`이다.
- batch 진행물 v67~v69: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v67은 중단 시점의 실제 50행을 보존하고 100행을 보충했으며, v69는 149→150행으로 보충했고 v68은 최초 완성 검사에서 통과했다. source SHA-256은 v67 `4eb624f380d3d3e4feeff3c67872598b1c17d3128eeacf7b4e4ee8a2e4e6e56f`, v68 `f8b1783be1ccf840591dab52aa63de4bbe72e58d9a5c8d4432eb32b88e2f6b7d`, v69 `2cce640aa476ee5ea1d608233c318788f33c7a5c42707e13cdcbab07d0bb2f47`이다.
- batch 진행물 v70~v72: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v70은 최초 완성 검사에서 통과했고, v71은 149→150행, v72는 148→150행으로 직접 보충했다. source SHA-256은 v70 `9fd8494a3ba227333945cb0d545cc1c43312d60715640272ff167c6a5f28187e`, v71 `e9aa344d0edb59c1e456ee5dfd0691d4c084889832e53fb1b10ce6e617181450`, v72 `7325958532f38f54c61337ca6fd9830ce060c09af83e0db69f6e675319462696`이다.
- batch 진행물 v73~v75: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v73은 148→150행, v74는 149→150행으로 보충했고 v75는 최초 완성 검사에서 통과했다. source SHA-256은 v73 `c7b3264c16b16d0efb1cfae9b83551c4aec053bd8afc4c801d11d8131ff42a1f`, v74 `ef742bb8e569c0187984c04ee617384cdd09fbe2952714b0a4a5f7ed381c49a5`, v75 `3f4c2eae9d68011fe07b1103b74cf117f9589ab2d40500ef1507feafb131a9ce`이다.
- batch 진행물 v76~v78: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v76은 중단 시점의 실제 50행을 보존하고 100행을 직접 보충한 뒤 기존 27번째 primary literal 불일치 1건을 직접 수정했으며, v77은 최초 149행에 1행을 보충했고 v78은 최초 99행 뒤 51행을 보충했다. source SHA-256은 v76 `0a4927c565a67edecd1ad0f1e280b37141511c2cfebdacbcf89a77997ec4d36a`, v77 `d5927ee4b4b8c3ef69cd121d56c6a1486f13b09ac0b581efa138f2d625e63e8d`, v78 `cccbf34f5a034a73c4c4f19e179f56ba3156883597d8d0c1964ecff0eb900962`이다.
- batch 진행물 v79~v81: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v79는 두 번째 묶음까지 101행을 직접 작성한 뒤 49행으로 맞췄고, v80은 50→99→150행, v81은 50→100→150행으로 완결했다. v81의 명백한 `않고 않고` 중복어 1건은 발견 즉시 직접 수정했다. source SHA-256은 v79 `2672a224ee01b1e7ba759dcb206036db4d963e7be246bc23255587c9db6d2d05`, v80 `6cd52003657a33fd1415b0d54f10bb11bfade917255aba016ce38b98f214e9da`, v81 `bbc61d5b5a34473032680bee7971e09fe9614d807885fdc28a05a6725d444be2`이다.
- batch 진행물 v82~v84: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v82는 두 번째 묶음 뒤 147행에 3행을 보충했고, v83과 v84는 50→100→150행으로 완결했다. source SHA-256은 v82 `8e6170463576998a3aba27f4da7df8c4f92c1427bd99b35ad967ff183600e08d`, v83 `f77d0e6381bfb56d0ecb9a049b0cab3736b63601f2065e3b747af889b0440330`, v84 `1b61a8711760e34dabe9ea1223bd591ca8fe8b38b1799e8f21d0e27a17b46d70`이다.
- batch 진행물 v85~v87: source 3개·450행 모두 parse·행 수·primary/text 고유성·통제 relations·관계 cardinality·primary literal 최소 계약 오류 0. v85는 최초 173행 초안에서 의미축에 충분한 선행 150행만 남겨 정확히 닫았고, v86은 50→100→150행, v87은 50→99→150행으로 완결했다. source SHA-256은 v85 `6d7e9a2e2903951d947f437855f9f12bd1cefd077028e2a747b2b3b368a944be`, v86 `db211804ab8306046d33989a367e94ce508a3ed3752a006f5e6e82859247929f`, v87 `0ea5ceff7cd606088df70aeb7777509f4feb28dbde6005d8245f9720b67d3352`이다.
- 2026-09-03 중단 checkpoint에서 남았던 5-word 반복 666종·초과 assignment 737건은 293행을 직접 재서술해 0으로 만들었다. 이어 파일 평균 초과 29개 source를 의미 보존 압축하고, word-set Jaccard 검토선 초과 1쌍을 v84에서 다시 설계했다. 2026-09-09 재감사에서 반복 4어절 도입부 8종이 추가로 확인되어 7개 version의 `text` 8건만 직접 재작성했다. 최종 A01 train 87 files·13,050 records의 파일 평균은 전부 `37.4625~45.7875` 범위 PASS, 전체 평균 `44.028889(+EOS)`다.
- A01 train 수정 정본 감사: source/corpus 87/87, artifact·exact/normalized/primary+relation-set·5-word·반복 4어절 도입부·통제 relation·hard 조사·review debt 오류 0. 문자 3~5-gram TF-IDF cosine `0.72` 이상 0쌍(최고 `0.623310`), word-set Jaccard `0.60` 이상 0쌍(최고 `0.545455`)이다. 조사 후보 965건은 `효과와/결과와`, `차이가/높이가`, `추가이익/추가이동` 내부 오탐으로 사람 검토해 확정 오류 0건이다.
- 2026-09-09 감사기 정정은 TF-IDF document frequency를 문서별 고유 feature로 계산하고 sparse index를 연속화했으며 CSR 검증·float64 cosine·벡터화 pair 순회를 적용했다. 수정 전 원고의 최고값은 독립 scikit-learn 전수 계산과 일치했으므로 과거 보고값 `0.618116915`는 데이터 변동이 아닌 감사기 계산 오류로 폐기한다. 또한 정본 set digest 산식과 validation 누출 gate를 바로잡고 반복 4어절 도입부를 0 gate로 추가했다.
- v40~v87 source-set digest는 `a11f857000801cb8b828067482e859b50c676afff368cfb121ca181270dff675`, corpus-set digest는 `84e9ec6f3f00bec253a8250a459f1c2504e9a8165cc226e2d153253b7b165879`다. checkpoint SHA-256은 `53898b28e550ed12697d6bff8eead70c8679020c72923efec1ec9d356ca5798f`이며 통합 보고서는 `../stage2_highdensity_dataset/audit_reports/TinyLM_Stage2_A01_CausalStructure_Train_Consolidated_Audit_2026-09-05.md`와 기계 부속에 보존한다.
- Stage2 부분 통합 재감사에서 validation v01 true set과 충돌한 train v85 112번째 relation-set 1건을 문장의 비교 의미에 맞춰 `attribute+comparison+other`로 보정했다. 보존 validation은 변경하지 않았고 definite leakage는 0으로 복구했다.
- Stage2 validation true slice의 전역 예약 set은 기존 v01이 이미 쓰는 정렬 relation-set 10종 `process+state`, `attribute+process`, `attribute+state`, `boundary+process`, `boundary+state`, `attribute+boundary`, `other+process`, `other+state`, `attribute+other`, `attribute+other+state`로 고정한다. A01 v02~v09는 이 10종만 재사용하고 이후 모든 Stage2 train source는 이를 사용하지 않는다. false slice는 현행 Stage2 train 관측 set만 쓴다.
- A01 train 종료 직후의 잠정 재개점: 기존 validation v01 pilot을 보존하고 `S2-A01-V-002~009`를 작성하는 안이었으나, 바로 다음 항목의 Stage train 완전 참조 gate 확인으로 순서를 정정했다.
- 실행 도구의 Stage train 완전 참조 gate와 §40.4의 train 우선 순서를 적용해 실제 다음 작성점은 `S2-A02-T-001`로 정정한다. A01 validation v02~v09 예약은 그대로 보존하며 Stage2 A02~A06 train 전체를 영역별 감사·포장한 뒤 작성한다.
- A02 재개 진행: `S2-A02-T-001~007` source-only 7 files·1,050 records를 직접 작성했고 각 파일 최소 계약 및 Stage2 validation true-set 금지 목록 충돌 0이다. 첫 domain `스마트 온실 관수·환경제어`의 다섯 axis를 완결했고 두 번째 domain `도시 상수도 정수·배수 운영`은 첫 두 axis까지 작성했다. token·5어절·fuzzy·조사 감사와 corpus 포장은 A02 86개 source 완결 뒤 일괄 수행한다. 다음은 `S2-A02-T-008`이다.
- A02 후속 진행: `S2-A02-T-008`의 기존 50행을 보존하고 100행을 직접 보충해 도시 상수도의 보호조건·제한 예외·해제 증거 범위를 150행으로 완결했다. canonical source 최소 계약, Stage2 validation 전역 금지 relation-set, A02 누적 1,200행 및 기존 Stage2 corpus exact 교차 중복 오류는 모두 0이며 source SHA-256은 `ada9c0654ad57f01ef495682378a6b1f0e184239b0b56127b1e003c991d8e66b`다. 영역 batch 감사·corpus 포장은 보류하고 다음은 `S2-A02-T-009`다.
- A02 후속 진행: `S2-A02-T-009` source 150행을 직접 작성해 도시 상수도의 자원 의존·공통고장·연쇄 실패 경로를 완결했다. A02 누적은 9 files·1,350 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v09 source SHA-256은 `d5ce712f95d7c72c8064b173ed0aaeb199483c0b9e07fbad46bc4b4d155294b2`이며 다음은 `S2-A02-T-010`이다.
- A02 후속 진행: `S2-A02-T-010` source 150행을 직접 작성해 도시 상수도의 조건 범위·기본 규칙 한계를 완결했다. 이로써 A02 v01~v10 10 files·1,500 source-only records와 두 domain의 각 다섯 axis가 완료됐다. 누적 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이고 v10 source SHA-256은 `8b77a863b44ba0a5404cdc4f79ad6cbe41f80446da89c771778485a11dfff1ca`다. 다음은 `S2-A02-T-011`이다.
- A02 후속 진행: `S2-A02-T-011` source 150행을 직접 작성해 클라우드 서비스의 필요조건·충분조건 방향 판정을 완결했다. A02 누적은 11 files·1,650 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v11 source SHA-256은 `3dc733684fa17aee5d738a7cc6107f914d42a0f92ac942c446f009182fb9016d`이며 다음은 `S2-A02-T-012`다.
- A02 후속 진행: `S2-A02-T-012` source 150행을 직접 작성해 클라우드 서비스의 선행 의존·독립 가능성 구분을 완결했다. A02 누적은 12 files·1,800 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v12 source SHA-256은 `e7fec27c4506917665011918b108882bd1e6a879cae20ce74bd8b6a14529d41f`이며 다음은 `S2-A02-T-013`이다.
- A02 후속 진행: `S2-A02-T-013` source 150행을 직접 작성해 클라우드 서비스의 보호조건·좁은 예외·해제증거 범위를 완결했다. A02 누적은 13 files·1,950 source-only records이고 최소 계약·exact 중복·Stage2 validation 금지 set 오류는 0이다. v13 source SHA-256은 `3053bf7abc674a8e0e7e72438261bcdebace36b131ab522ac02250771b3424ab`이며 다음은 `S2-A02-T-014`다.
- A02 후속 진행: `S2-A02-T-014` source 150행을 직접 작성해 클라우드 서비스의 자원 의존·공통고장·연쇄 실패를 완결했다. A02 누적은 14 files·2,100 source-only records이고 최소 계약·exact 중복·Stage2 validation 금지 set 오류는 0이다. v14 source SHA-256은 `fda9e3d29d278387e1b34988c4351d9473e7914d4be7dbc469eca95687b40046`이며 다음은 `S2-A02-T-015`다.
- A02 후속 진행: `S2-A02-T-015` source 150행을 직접 작성해 클라우드 서비스의 조건문 범위·기본 규칙 한계를 완결했다. 이로써 A02 v01~v15 15 files·2,250 source-only records와 세 domain의 각 다섯 axis가 완료됐다. 누적 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이고 v15 source SHA-256은 `ea2bcb0b43e96d55f8ef101849a15e69ee885eea49a5f6385df66a53bf108350`이다. 다음은 철도 domain의 `S2-A02-T-016`이다.
- A02 후속 진행: `S2-A02-T-016` source 150행을 직접 작성해 철도 운행 간격·환승 조정에서 필요조건과 충분조건의 방향 판정을 완결했다. A02 누적은 16 files·2,400 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v16 source SHA-256은 `2b1eb73af7deaf015e972fc7eb53b387a002a53d220e08fc07e354d01f481ef3`이며 다음은 같은 domain의 선행 의존·독립 가능성 축 `S2-A02-T-017`이다.
- A02 후속 진행: `S2-A02-T-017` source 150행을 직접 작성해 철도 운행 간격·환승 조정에서 선행 의존과 제한적 독립 가능성 구분을 완결했다. A02 누적은 17 files·2,550 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v17 source SHA-256은 `5c58b0b114004e06c6bc8eae4f9ab904151d8bf41fdf1309507b6764e1cccf0e`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-018`이다.
- A02 후속 진행: `S2-A02-T-018` source 150행을 직접 작성해 철도 운행 간격·환승 조정에서 보호조건·예외·해제조건의 범위를 완결했다. A02 누적은 18 files·2,700 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v18 source SHA-256은 `17099c1370b2765a6ba6cf8471bc084038f04ae3220846009b64bd0beb63709c`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-019`다.
- A02 후속 진행: `S2-A02-T-019` source 150행을 직접 작성해 철도 운행 간격·환승 조정에서 자원 의존과 연쇄 실패 경로를 완결했다. A02 누적은 19 files·2,850 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v19 source SHA-256은 `56197935e6b7a0a36df858ab2e6b526bacce1e3aae5f3956d5e71434be1f8d4c`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-020`이다.
- A02 후속 진행: `S2-A02-T-020` source 150행을 직접 작성해 철도 운행 간격·환승 조정에서 조건문 범위와 기본 규칙의 한계를 완결했다. 이로써 철도 domain의 다섯 axis와 A02 v01~v20 20 files·3,000 source-only records가 완료됐다. 누적 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이고 v20 source SHA-256은 `d7c6fd9615666cb2f29aa36bf535275404966c557374f1fd7b5e69c2a5729bd5`이다. 다음은 하천 저수지 수위·방류 관리 domain의 `S2-A02-T-021`이다.
- A02 후속 진행: `S2-A02-T-021` source 150행을 직접 작성해 하천 저수지 수위·방류 관리에서 필요조건과 충분조건의 방향 판정을 완결했다. A02 누적은 21 files·3,150 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v21 source SHA-256은 `29961db71abe62106e2808b81624808d97f73a14d4c1194d2bced7373344d3ce`이며 다음은 선행 의존·독립 가능성 축 `S2-A02-T-022`다.
- A02 후속 진행: `S2-A02-T-022` source 150행을 직접 작성해 하천 저수지 수위·방류 관리에서 선행 의존과 제한적 독립 가능성 구분을 완결했다. A02 누적은 22 files·3,300 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v22 source SHA-256은 `13650ab31a8ad93353e272088b23496f782a895a264de2ccbb71b6937702edc2`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-023`이다.
- A02 후속 진행: `S2-A02-T-023` source 150행을 직접 작성해 하천 저수지 수위·방류 관리에서 보호조건·예외·해제조건의 범위를 완결했다. A02 누적은 23 files·3,450 source-only records이고 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v23 source SHA-256은 `ae22d5eed7aadc97bb730141540e6de75be9422617f6ec4502c3db6b57d3eb94`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-024`다.
- A02 후속 진행: `S2-A02-T-024` source 150행을 직접 작성해 하천 저수지 수위·방류 관리에서 자원 의존과 연쇄 실패 경로를 완결했다. A02 누적은 24 files·3,600 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v24 source SHA-256은 `01e4880be939e3069ec2a5711a380557c6c503022f9215016af05d6e12be67cf`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-025`다.
- A02 후속 진행: `S2-A02-T-025` source 150행을 직접 작성해 하천 저수지 수위·방류 관리에서 조건문 범위와 기본 규칙의 한계를 완결했다. 후속 최소 검사에서 중복 오탈자 1건을 수정했으며 A02 누적은 25 files·3,750 source-only records, canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. 최종 v25 source SHA-256은 `e793c10f547a0ca341ea28c91ed823c6b61b85094d54ab26ac2442e66a4a16cb`이며 해당 domain의 다섯 axis가 끝났다. 다음은 새 domain 식품 냉장 유통·품질 유지의 필요·충분조건 축 `S2-A02-T-026`이다.
- A02 후속 진행: `S2-A02-T-026` source 150행을 직접 작성해 식품 냉장 유통·품질 유지에서 필요조건과 충분조건의 방향 판정을 완결했다. A02 누적은 26 files·3,900 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v26 source SHA-256은 `8879207e92a2ea2aee6e281be14e123088acd8dca47a37f6500e282995032351`이며 다음은 선행 의존·독립 가능성 축 `S2-A02-T-027`이다.
- A02 후속 진행: `S2-A02-T-027` source 150행을 직접 작성해 식품 냉장 유통·품질 유지에서 선행 의존과 제한적 독립 가능성 구분을 완결했다. A02 누적은 27 files·4,050 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v27 source SHA-256은 `b8ccd4f41d6f4175dbfb50ed78748bdda73cac0d96dfb44f2f88b54ebfd5e3ab`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-028`이다.
- A02 후속 진행: `S2-A02-T-028` source 150행을 직접 작성해 식품 냉장 유통·품질 유지에서 보호조건·제한 예외·독립 해제증거의 범위를 완결했다. A02 누적은 28 files·4,200 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v28 source SHA-256은 `d262e75ce5ad26cff9b6b5f54160d61dd4224e620155974e220877acd21370a0`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-029`다.
- A02 후속 진행: `S2-A02-T-029` source 150행을 직접 작성해 식품 냉장 유통·품질 유지에서 자원 의존과 연쇄 실패 경로를 완결했다. A02 누적은 29 files·4,350 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v29 source SHA-256은 `efd5c33b75f35a6585e28a39dce135aeffd56ccc905494f96e822bbd71f61781`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-030`이다.
- A02 후속 진행: `S2-A02-T-030` source 150행을 직접 작성해 식품 냉장 유통·품질 유지에서 조건문 범위와 기본 규칙의 한계를 완결했다. A02 누적은 30 files·4,500 source-only records이고 canonical 최소 계약·exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v30 source SHA-256은 `dbaf33e67be4794f0b5d7351f249fd1e510ea7acbdcc1e6ed65dafbcbea8f3a3`이며 해당 domain의 다섯 axis가 끝났다. 다음은 새 domain 온라인 학습 진도·피드백 운영의 필요·충분조건 축 `S2-A02-T-031`이다.
- A02 후속 진행: `S2-A02-T-031`은 중단 전 100행을 보존하고 50행을 직접 보충해 온라인 학습 진도·피드백 운영에서 필요조건과 충분조건의 방향 판정을 완결했다. A02 누적은 31 files·4,650 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v31 source SHA-256은 `d2f8f765ea9921dac84e5ab63ef4bd0212d76313e42594b1b428a5f2ebff11c3`이며 다음은 같은 domain의 선행 의존·독립 가능성 축 `S2-A02-T-032`다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-032` source 150행을 직접 작성해 온라인 학습 진도·피드백 운영의 선행 의존과 병렬·독립 가능성 구분을 완결했다. 151→150행 조정과 선후 표현 1건 수정 뒤 A02 누적은 32 files·4,800 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v32 source SHA-256은 `49be22d8d44b2aec8aa5f12fa0299dbfe03be31399d8c3c347e1be43e814e584`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-033`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-033` source 150행을 직접 작성해 온라인 학습 진도·피드백 운영의 보호조건·제한 예외·해제증거 범위를 완결했다. primary literal 누락 2건 수정 뒤 A02 누적은 33 files·4,950 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v33 source SHA-256은 `0273c0ff624660949345dea10844bc5f361a61add75ee512040e4337c4100784`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-034`다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-034` source는 온라인 학습 진도·피드백 운영의 공유 자원·병목·공통원인·연쇄 실패 경로를 150행으로 완결했다. 최초 149행에 1행을 보충한 뒤 A02 누적은 34 files·5,100 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v34 source SHA-256은 `3c873b11949d524602f496be5091f29fe5fee22e6192fc4ad3c734af66cff8c8`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-035`다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-035` source 150행을 직접 작성해 온라인 학습 진도·피드백 운영의 조건문 범위와 기본 규칙 한계를 완결했다. A02 누적은 35 files·5,250 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v35 source SHA-256은 `b9e7e55c826cb62b5667b9eaecf5b1e289e463272beaa481fe204906dc525dd3`이며 온라인 학습 domain의 다섯 axis가 모두 끝났다. 다음은 새 domain 생태 복원지 종·서식지 관찰의 필요·충분조건 축 `S2-A02-T-036`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-036` source 150행을 직접 작성해 생태 복원지 종·서식지 관찰에서 필요조건과 충분조건의 방향 판정을 완결했다. 151→150행 조정 뒤 A02 누적은 36 files·5,400 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v36 source SHA-256은 `b55df6b93542991dbfef1cb182ff829c874283c6205547bcf55a71f61f05b26f`이며 다음은 선행 의존·독립 가능성 축 `S2-A02-T-037`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-037` source 150행을 직접 작성해 생태 복원지 종·서식지 관찰의 선행 의존과 병렬·독립 가능성 구분을 완결했다. 조사 오류 1건 수정 뒤 A02 누적은 37 files·5,550 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v37 source SHA-256은 `662bce8179c0177e3ea48eccd0bc8020b1b9cdd4d652a8d67aed1ceba1c55690`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-038`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-038` source는 생태 복원지 종·서식지 관찰의 보호조건·제한 예외·해제증거 범위를 150행으로 완결했다. 최초 149행에 1행을 보충한 뒤 A02 누적은 38 files·5,700 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v38 source SHA-256은 `65d6f24336df8ea82502aa94c9f048aedbdbb4cb3d289f8f1e2247f04dfcfc2b`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-039`다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-039` source 150행을 직접 작성해 생태 복원지 종·서식지 관찰의 자원 의존과 공통고장·연쇄 실패 경로를 완결했다. 중단 시점의 100행을 보존하고 50행만 보충했으며 명백한 서술 오류 1건을 수정했다. A02 누적은 39 files·5,850 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v39 source SHA-256은 `366176876316b137d12dd0cc860c479ce6a97d5ddf0aa5789427a5ff9a208495`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-040`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-040` source 150행을 직접 작성해 생태 복원지 종·서식지 관찰의 조건문 범위와 기본 규칙 한계를 완결했다. A02 누적은 40 files·6,000 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v40 source SHA-256은 `4b49e76619fb4d575bdeeca892f1e9582363e665a78d8d95846b931d3109de73`이며 생태 복원지 domain의 다섯 axis가 모두 끝났다. 다음은 새 domain 배터리 저장장치 충방전·열관리의 필요·충분조건 축 `S2-A02-T-041`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-041` source 150행을 직접 작성해 배터리 저장장치 충방전·열관리의 필요조건과 충분조건 방향 판정을 완결했다. 149→150행 보충과 어색한 primary 1건 정리 뒤 A02 누적은 41 files·6,150 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v41 source SHA-256은 `89808a5c7eb2720e15041178b98a132373addd293ebc99a01f8f58480529327a`이며 다음은 선행 의존·독립 가능성 축 `S2-A02-T-042`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-042` source 150행을 직접 작성해 배터리 저장장치 충방전·열관리의 선행 의존과 병렬·독립 가능성 구분을 완결했다. A02 누적은 42 files·6,300 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v42 source SHA-256은 `587bd0a1ea800d5144bea0cd27bc18f30cca56930fcd1e69dc0476ae18b6e0c4`이며 다음은 보호조건·예외·해제조건 범위 축 `S2-A02-T-043`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-043` source 150행을 직접 작성해 배터리 저장장치 충방전·열관리의 보호조건·제한 예외·해제증거 범위를 완결했다. A02 누적은 43 files·6,450 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v43 source SHA-256은 `d58c47998d1bf4916e87819afb45064d9e558e3ace9402a829a12fcb972d5c0e`이며 다음은 자원 의존·연쇄 실패 경로 축 `S2-A02-T-044`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-044` source 150행을 직접 작성해 배터리 저장장치 충방전·열관리의 자원 의존과 공통고장·연쇄 실패 경로를 완결했다. 149→150행 보충 뒤 A02 누적은 44 files·6,600 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v44 source SHA-256은 `d564870bcbe04ae280162ec78eeb6427821cd10ff86c79cb10485bfdb7173c4a`이며 다음은 조건문 범위·기본 규칙 한계 축 `S2-A02-T-045`이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 후속 진행: `S2-A02-T-045` source 150행을 직접 작성해 배터리 저장장치 충방전·열관리의 조건문 범위와 기본 규칙 한계를 완결했다. 149→150행 보충 뒤 A02 누적은 45 files·6,750 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v45 source SHA-256은 `2fcf8888eba801ef4e2dad5cd6443ed6eff7de45d2f8c9cc34aeb4127e640182`이며 배터리 저장장치 domain의 다섯 axis가 모두 끝났다. 다음은 contingency 예약 `S2-A02-T-046`(`S2-R-04`)의 지하철 역사 환기·혼잡 제어 — 다중 원인과 예외 조합이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 contingency 진행: `S2-A02-T-046`(`S2-R-04`) source 150행을 직접 작성해 지하철 역사 환기·혼잡 제어의 다중 원인과 제한 예외 조합을 완결했다. A02 누적은 46 files·6,900 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v46 source SHA-256은 `ab47b99ee60ab06ccb8b248c14d6e670fabaaa2deef0cd5cf533518130904b3c`이며 다음은 contingency `S2-A02-T-047`(`S2-R-06`)의 수산 양식장 수질·급이 운영 — 희귀 조건에서 인과·조건 분리다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 contingency 진행: `S2-A02-T-047`(`S2-R-06`) source 150행을 직접 작성해 수산 양식장 수질·급이 운영에서 희귀 수질·생리·장비·기상 조건의 인과 분리와 역추론 한계를 완결했다. 중단된 첫 도구 호출 뒤 실제 반영된 50행을 보존하고 100행만 보충했으며 어색한 결합과 띄어쓰기 2건을 직접 수정했다. A02 누적은 47 files·7,050 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v47 source SHA-256은 `bb3ba51b7dc1cba4e38fff9f0a6772aeb29800d2ebe5048ef6f217db44157549`이며 다음은 contingency `S2-A02-T-048`(`S2-R-14`)의 태양광 발전소 출력·고장 관리 — 다중 원인과 예외 조합이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 contingency 진행: `S2-A02-T-048`(`S2-R-14`) source 150행을 직접 작성해 태양광 발전소 출력·고장 관리의 기상·설비·계통·진단·정비·재난 조건에서 다중 원인과 제한 예외 조합을 완결했다. A02 누적은 48 files·7,200 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v48 source SHA-256은 `bfbc15720664e830a12b4a86f2116d75e244074a97c1585cef04af5669d01296`이며 다음은 contingency `S2-A02-T-049`(`S2-R-16`)의 응급 콜센터 배차·인계 — 희귀 조건에서 인과·조건 분리다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 contingency 진행: `S2-A02-T-049`(`S2-R-16`) source 150행을 직접 작성해 응급 콜센터 배차·인계의 신고·위치·위험 분류·출동·현장 접근·성과평가에서 희귀 조건에 따른 인과 분리와 선택편향을 완결했다. A02 누적은 49 files·7,350 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v49 source SHA-256은 `eb2f7d7a46e1ed9e4bec140d6e9a877baf9def34a21962deaeab268e740c8e21`이며 다음은 primary 예약 `S2-A02-T-050`의 공항 활주로 제설·운항 회복 — 필요조건 충족과 결과 발생의 비대칭 판정이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-050` source 150행을 직접 작성해 공항 활주로 제설·운항 회복에서 필요조건 충족과 실제 결과 발생의 비대칭을 완결했다. 50+49행 중간 실측에 따라 마지막 묶음을 51행으로 조정하고 항공 용어 1건을 바로잡았다. A02 누적은 50 files·7,500 source-only records이고 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v50 source SHA-256은 `ea6e249733d435ee4db991790c995363c6eb603cdf0e8999ddc9927e4ae59c46`이며 다음은 primary 예약 `S2-A02-T-051`의 반도체 클린룸 오염·수율 관리 — 선행 자원 의존과 독립 우회경로 구분이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-051` source 150행을 직접 작성해 반도체 클린룸 오염·수율 관리의 공조·유틸리티·공정·계측·계보·공급망에서 선행 자원 의존과 제한적 독립 우회경로를 완결했다. 필드 오타 1건, 조사 오류 1건과 가독성 표현 5건을 정리한 뒤 A02 누적은 51 files·7,650 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v51 source SHA-256은 `da136b23bdfa5b76b3cd679739c5866208f518bde162f0c80c3ff047ad5f74ea`이며 다음은 primary `S2-A02-T-052`의 도시 열공급망 부하·압력 조정 — 보호조건 해제 시 예외 적용 범위 추적이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-052` source 150행을 직접 작성해 도시 열공급망 부하·압력 조정에서 보호조건 해제의 시작·종료 근거와 구역·시간·역할별 예외 범위를 완결했다. 두 중간 묶음의 49행 실측에 따라 보충량을 조정하고 가독성·의미 표현 4건을 정리한 뒤 A02 누적은 52 files·7,800 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v52 source SHA-256은 `577d6502348135807cab4714bd51cead3ff3f7ec7c6d9cc849205cb4142323bf`이며 다음은 primary `S2-A02-T-053`의 해양 부표 관측·경보 운영 — 연쇄 실패에서 최초 의존 고리 식별이다. 다음 파일부터는 source 150행을 한 번에 작성하며 token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-053` source 150행을 한 번에 직접 작성해 해양 부표 관측·경보 운영의 전원·센서·로거·통신·육상처리·계류·정비·경보 전달에서 연쇄 실패의 최초 의존 고리 식별을 완결했다. 일괄 패치가 정확히 150행이었고 표현 4건을 정리한 뒤 A02 누적은 53 files·7,950 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v53 source SHA-256은 `67b54531f88c4d55cc80feb25ab461f8a3faf519bae1586ba4d79862cc299438`이며 다음은 primary `S2-A02-T-054`의 병원 수술실 배정·감염 통제 — 기본 규칙과 조건부 재정의의 우선순위다. 이후 파일도 source 150행 일괄 작성 규칙을 유지하며 token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-054` source를 전체 파일 단위로 직접 작성해 병원 수술실 배정·감염 통제에서 기본 규칙과 조건부 재정의의 우선순위를 완결했다. 최초 일괄본 151행에서 의미 범위가 겹치는 일반 직원건강 record 1행을 제거하고 표현 9건을 정리한 뒤 A02 누적은 54 files·8,100 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v54 source SHA-256은 `750b0d0675bbae8cc455bc9dca8491cf1a3961b9585f209ed03bcc13639955f0`이며 다음은 primary `S2-A02-T-055`의 산림 병해충 예찰·방제 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 이후 파일은 일괄 작성 직후 150행 gate를 우선 적용하고 token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-055` source 150행을 적용 전 행수 guard를 둔 단일 전체 파일 패치로 직접 작성해 산림 병해충 예찰·방제에서 필요조건 충족과 결과 발생의 비대칭 판정을 완결했다. 최초 적용부터 150행이었고 표현 25건을 정리한 뒤 A02 누적은 55 files·8,250 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v55 source SHA-256은 `a5bcbc3afbd8f939e5af4dd0fec0b833c5efd55b14c341f8cf987c6406dc11b4`이며 다음은 primary `S2-A02-T-056`의 전기버스 충전차고 전력·배차 — 선행 자원 의존과 독립 우회경로 구분이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-056` source는 적용 전 149행 초안을 차단하고 누락된 배차제어실 우회 단위를 보충한 150행 전체 패치만 반영해 전기버스 충전차고 전력·배차의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 표현 28건을 정리한 뒤 A02 누적은 56 files·8,400 source-only records이며 canonical 최소 계약·primary/text exact 중복·기존 Stage2 corpus exact 교차 중복·Stage2 validation 금지 set 오류는 0이다. v56 source SHA-256은 `e6dce85b4ff5e4c93af1de0f59f8864fccfc70743df5064b11f557a5b02a506e`이며 다음은 primary `S2-A02-T-057`의 식품 발효공정 온도·품질 제어 — 보호조건 해제 시 예외 적용 범위 추적이다. token·5어절·fuzzy·조사 전수 감사와 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-057` source 150행을 적용 전 행수 guard를 둔 단일 전체 파일 패치로 직접 작성해 식품 발효공정 온도·품질 제어에서 보호조건 해제 시 예외 적용 범위 추적을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 57 files·8,550 source-only records다. v57 source SHA-256은 `2380c6a10d38d788ca15937f8ab96210a3cf393a013a9ecd58e2241349addbff`이며 다음은 primary `S2-A02-T-058`의 데이터센터 냉각·전력 절체 — 연쇄 실패에서 최초 의존 고리 식별이다. 새 지침에 따라 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-058` source 150행을 단일 전체 파일 패치로 직접 작성해 데이터센터 냉각·전력 절체의 전원·배전·정보처리·냉수·공조·감지·안전·운영 사슬에서 연쇄 실패의 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 58 files·8,700 source-only records다. v58 source SHA-256은 `d507ab9cf5a3aa262b46d1bec1eb36b0f49aab5f2ab1fc3a6c629d59dea5a59c`이며 다음은 primary `S2-A02-T-059`의 항만 컨테이너 하역·혼잡 관리 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-059` source는 적용 전 164행 초안을 차단하고 겹치는 후반 권한·예외 축 14개를 제외한 150행 전체 패치만 반영해 항만 컨테이너 하역·혼잡 관리의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 59 files·8,850 source-only records다. v59 source SHA-256은 `603167c7e84bbf062f287de9e78727637f970e073c331e46a9ec3c2c0bdf403f`이며 다음은 primary `S2-A02-T-060`의 스마트 축사 환기·질병 감시 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-060` source는 적용 전 144행·149행 초안을 차단하고 누락된 판단축을 보완한 150행 전체 패치만 반영해 스마트 축사 환기·질병 감시의 필요조건 충족과 결과 발생 비대칭을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 60 files·9,000 source-only records다. v60 source SHA-256은 `5e65ea5e6af998657c53cb40d839355bbad449565dc46e3ab07dfc510d7cc8b5`이며 다음은 primary `S2-A02-T-061`의 도로 터널 배수·교통 통제 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-061` source는 적용 전 151행 초안을 차단하고 중복 의미축 1개를 제외한 150행 전체 패치만 반영해 도로 터널 배수·교통 통제의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 61 files·9,150 source-only records다. v61 source SHA-256은 `338fb5256b2817ae80c3b5e9db4e598a700bb03b0cfb25851340878ed7598e1f`이며 다음은 primary `S2-A02-T-062`의 공항 활주로 제설·운항 회복 — 보호조건 해제 시 예외 적용 범위 추적이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-062` source 150행을 첫 단일 전체 파일 패치로 직접 작성해 공항 활주로 제설·운항 회복의 보호조건 해제 시 예외 적용 범위와 재폐쇄 조건을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 62 files·9,300 source-only records다. v62 source SHA-256은 `2d7259a6b5f48ff209ee78016764dd87ca0d467140651a69d41a13c09f638740`이며 다음은 primary `S2-A02-T-063`의 반도체 클린룸 오염·수율 관리 — 연쇄 실패에서 최초 의존 고리 식별이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-063` source 150행을 첫 단일 전체 파일 패치로 직접 작성해 반도체 클린룸 오염·수율 관리의 공조·유틸리티·재료·물류·공정·계측·자료계보 연쇄에서 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 63 files·9,450 source-only records다. v63 source SHA-256은 `402e93faa6497227ac0e7e10f311c567c87b1fdc5c769c1385887f7ddb95eef6`이며 다음은 primary `S2-A02-T-064`의 도시 열공급망 부하·압력 조정 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-064` source 150행을 첫 단일 전체 파일 패치로 직접 작성해 도시 열공급망 부하·압력 조정의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 64 files·9,600 source-only records다. v64 source SHA-256은 `97fab6eeea675f7f2259a63dcca4b181d65e132d81d77f63b72954ed8c2c26cd`이며 다음은 primary `S2-A02-T-065`의 해양 부표 관측·경보 운영 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-065` source는 최초 151행에서 의미가 인접한 1행을 제외한 150행으로 해양 부표 관측·경보 운영의 필요조건 충족과 결과 발생 비대칭을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 65 files·9,750 source-only records다. v65 source SHA-256은 `e1461aebe2a4e9512882a3ee8fc35d12f015cd8c20158068e43a0c082a430c84`이며 다음은 primary `S2-A02-T-066`의 병원 수술실 배정·감염 통제 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-066` source는 최초 152행에서 격리표지·감염사건 종료와 의미가 인접한 2행을 제외한 150행으로 병원 수술실 배정·감염 통제의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 66 files·9,900 source-only records다. v66 source SHA-256은 `d990d974a45e101cdae1ba340a7e0438436c23de80e0748ab8fd59b6bd2e0cae`이며 다음은 primary `S2-A02-T-067`의 산림 병해충 예찰·방제 — 보호조건 해제 시 예외 적용 범위 추적이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-067` source는 최초 152행에서 후속감시·접근제한과 의미가 인접한 2행을 제외한 150행으로 산림 병해충 예찰·방제의 보호조건 해제 시 예외 적용 범위를 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 67 files·10,050 source-only records다. v67 source SHA-256은 `be99e7454adc319c4fbc2b948a81eda03ea8667f54535621dfbf7ace0299106a`이며 다음은 primary `S2-A02-T-068`의 철도 신호·운행복구 — 연쇄 실패에서 최초 의존 고리 식별이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-068` source는 최초 156행에서 통신·정비·예방제한·승객서비스·후속감시·동시각 기록의 인접 축 6행을 제외한 150행으로 철도 신호·운행복구 연쇄의 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 68 files·10,200 source-only records다. v68 source SHA-256은 `390aa99a5122d09dc35c4f1ea2767f818263941f342ab14f60cd07a79e845377`이며 다음은 primary `S2-A02-T-069`의 식품 발효공정 온도·품질 제어 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-069` source는 최초 156행에서 숙성예약·보호복·세척표본·재작업혼합·교대인계·부분로트 해제의 인접 축 6행을 제외한 150행으로 식품 발효공정 온도·품질 제어의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 69 files·10,350 source-only records다. v69 source SHA-256은 `21bae4827bdb161e5d10a4ba9b7eddde6e7b9443145f8383c4cbf571fcc84f40`이며 다음은 primary `S2-A02-T-070`의 데이터센터 냉각·전력 절체 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-070` source는 최초 156행에서 인접 의미축 6행을 제외한 150행으로 데이터센터 냉각·전력 절체의 필요조건 충족과 결과 발생 비대칭을 완결했다. v73 최소 검사 중 A02 누적 primary exact 중복 1건을 발견해 v70의 일반형 primary를 냉동기 도메인 한정형으로 재서술했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 70 files·10,500 source-only records다. 최종 v70 source SHA-256은 `02548e0ade1f3a02ae4833f3abaedf1e7401381e50eed67f39a24f07e9af18ef`이며 다음은 primary `S2-A02-T-071`의 항만 컨테이너 하역·혼잡 관리 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-071` source는 148행 초안의 편집 잔여문구·조사 오류를 고치고 샤시 조달·이동검색차 우회 2행을 직접 보완한 150행으로 항만 컨테이너 하역·혼잡 관리의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 71 files·10,650 source-only records다. v71 source SHA-256은 `b5f799b762f1f26a83115df7623355138a4238ef7f7b68313f199de1b302b90a`이며 다음은 primary `S2-A02-T-072`의 스마트 축사 환기·질병 감시 — 보호조건 해제 시 예외 적용 범위 추적이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-072` source는 최초 149행에서 `봉인 차량` 관련 조사 2건을 바로잡고 임시필터 우회 1행을 직접 보완한 150행으로 스마트 축사 환기·질병 감시의 보호조건 해제 시 예외 적용 범위를 완결했다. 단일 파일 canonical 최소 계약과 150/150 primary/text 고유성을 확인했고 A02 진행은 72 files·10,800 source-only records다. v72 source SHA-256은 `cb12418d1e2eb895663c5c43c521dcc0c7e5b7472c3dd2523979b50178b72df4`이며 다음은 primary `S2-A02-T-073`의 도로 터널 배수·교통 통제 — 연쇄 실패에서 최초 의존 고리 식별이다. 파일별 토큰·유사도·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-073` source는 최초 154행에서 인접 일반축 4행을 제외한 150행으로 도로 터널 배수·교통 통제 연쇄의 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약과 Stage2 validation 금지 set 오류는 0이다. 누적 exact gate에서 드러난 v60·v70 primary 중복 1건은 v70을 도메인 한정 재서술해 해소했고 A02 v01~v73 73 files·10,950 records의 primary/text exact 중복은 0이다. v73 source SHA-256은 `6dac6daa96616dc32db736dc26b4112f2a1a0dff9b5230a5d68b197d56d2ae93`이며 다음은 primary `S2-A02-T-074`의 공항 활주로 제설·운항 회복 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-074` source는 최초 141행에 누락 판단축 9행을 직접 보완한 150행으로 공항 활주로 제설·운항 회복의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v74 74 files·11,100 records 누적 primary/text exact 중복 오류는 0이다. v74 source SHA-256은 `4ae9f9245e7f4cc0f28a0ff248ba7ee18fa654afabca7791f002d95a993858c8`이며 다음은 primary `S2-A02-T-075`의 반도체 클린룸 오염·수율 관리 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-075` source는 최초 139행에 누락 판단축 11행을 직접 보완한 150행으로 반도체 클린룸 오염·수율 관리의 필요조건 충족과 결과 발생 비대칭을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v75 75 files·11,250 records 누적 primary/text exact 중복 오류는 0이다. v75 source SHA-256은 `185c391eb5d78211386fd4e74fb45ff5232b4f08a18cc17cfe590b82cce0b2d0`이며 다음은 primary `S2-A02-T-076`의 도시 열공급망 부하·압력 조정 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-076` source는 최초 115행의 primary literal 4건을 고치고 누락 판단축 35행을 직접 보완한 150행으로 도시 열공급망 부하·압력 조정의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v76 76 files·11,400 records 누적 primary/text exact 중복 오류는 0이다. v76 source SHA-256은 `982b6d15f0b353f969784dcf15d3ffd22b9fa9d78d0566e43ba5c4ea5febac06`이며 다음은 primary `S2-A02-T-077`의 해양 부표 관측·경보 운영 — 보호조건 해제 시 예외 적용 범위 추적이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-077` source는 최초 104행에 누락 판단축 46행을 직접 보완한 150행으로 해양 부표 관측·경보 운영의 보호조건 해제 시 예외 적용 범위를 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v77 77 files·11,550 records 누적 primary/text exact 중복 오류는 0이다. v77 source SHA-256은 `e1cc01411faddc0cfe5824ecff6a041e6f4952195e961f3a47e50523b9ff3081`이며 다음은 primary `S2-A02-T-078`의 병원 수술실 배정·감염 통제 — 연쇄 실패에서 최초 의존 고리 식별이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-078` source는 최초 81행의 편집 잔여문구 1건을 고치고 누락 판단축 69행을 직접 보완한 150행으로 병원 수술실 배정·감염 통제 연쇄의 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v78 78 files·11,700 records 누적 primary/text exact 중복 오류는 0이다. v78 source SHA-256은 `a7d2cfd7879325e1faf64cfa1f237204eba2bbbcfc11b13dd9e110f930cba5b5`이며 다음은 primary `S2-A02-T-079`의 산림 병해충 예찰·방제 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-079` source는 최초 151행에서 인접 공개축 1행을 제외한 150행으로 산림 병해충 예찰·방제의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v79 79 files·11,850 records 누적 primary/text exact 중복 오류는 0이다. v79 source SHA-256은 `eff1eec2717ee7c7fc533a9a4da972f2b41ffcff8e925621e2c14e5fe1b6b260`이며 다음은 primary `S2-A02-T-080`의 전기버스 충전차고 전력·배차 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-080` source 150행을 두 번의 직접 작성 패치로 완성해 전기버스 충전차고 전력·배차의 필요조건 충족과 결과 발생 비대칭을 다뤘다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v80 80 files·12,000 records 누적 primary/text exact 중복 오류는 0이다. v80 source SHA-256은 `2b88bbb490dcebf6fa9a75df35109ba67764cafa60a5e957584e2845d2bed35d`이며 다음은 primary `S2-A02-T-081`의 식품 발효공정 온도·품질 제어 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-081` source는 최초 149행에 비상용수 안전정지 범위 1행을 직접 보완한 150행으로 식품 발효공정 온도·품질 제어의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v81 81 files·12,150 records 누적 primary/text exact 중복 오류는 0이다. v81 source SHA-256은 `ee139c2c7693ccff1edfe3d7241295e88fec22c67bd61df8cbb8b0ba0ad7063d`이며 다음은 primary `S2-A02-T-082`의 데이터센터 냉각·전력 절체 — 보호조건 해제 시 예외 적용 범위 추적이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-082` source 150행을 50행씩 세 묶음으로 직접 작성해 데이터센터 냉각·전력 절체의 보호조건 해제와 예외 적용 범위를 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v82 82 files·12,300 records 누적 primary/text exact 중복 오류는 0이다. v82 source SHA-256은 `90012dcd038a41f665e9284ce35870b62cb4533c2599861833b0ffd72b76810d`이며 다음은 primary `S2-A02-T-083`의 항만 컨테이너 하역·혼잡 관리 — 연쇄 실패에서 최초 의존 고리 식별이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-083` source는 50행·49행·51행의 세 직접 작성 묶음으로 150행을 맞춰 항만 컨테이너 하역·혼잡 연쇄의 최초 의존 고리 식별을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v83 83 files·12,450 records 누적 primary/text exact 중복 오류는 0이다. v83 source SHA-256은 `26ba5b52715d9d44cd813bad1973e788e74c8fc638b3640e3cfb600caeb5f99b`이며 다음은 primary `S2-A02-T-084`의 스마트 축사 환기·질병 감시 — 기본 규칙과 조건부 재정의의 우선순위다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-084` source는 최초 149행에 복수조건 우선순위 1행을 직접 보완한 150행으로 스마트 축사 환기·질병 감시의 기본 규칙과 조건부 재정의 우선순위를 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v84 84 files·12,600 records 누적 primary/text exact 중복 오류는 0이다. v84 source SHA-256은 `2a089b107d442e60cad43aa9c99ec564b67b707d289fa66a10730045509a720f`이며 다음은 primary `S2-A02-T-085`의 도로 터널 배수·교통 통제 — 필요조건 충족과 결과 발생의 비대칭 판정이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 진행: `S2-A02-T-085` source는 50행·49행·51행의 세 직접 작성 묶음으로 150행을 맞춰 도로 터널 배수·교통 통제의 필요조건 충족과 결과 발생 비대칭을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v85 85 files·12,750 records 누적 primary/text exact 중복 오류는 0이다. v85 source SHA-256은 `03c00ade398d876bb0cfee4f7bd1da86aa5ecb5ed1c8b603b8e60c7814327929`이며 다음은 primary `S2-A02-T-086`의 공항 활주로 제설·운항 회복 — 선행 자원 의존과 독립 우회경로 구분이다. 파일별 token·fuzzy·n-gram·조사·표현 교정과 누적 감사 및 corpus 포장은 A02 v86 완결 뒤 일괄 수행한다.
- A02 primary 완결: `S2-A02-T-086` source 150행을 50행씩 세 묶음으로 직접 작성해 공항 활주로 제설·운항 회복의 선행 자원 의존과 독립 우회경로 구분을 완결했다. 단일 파일 canonical 최소 계약·Stage2 validation 금지 set과 A02 v01~v86 86 files·12,900 records 누적 primary/text exact 중복 오류는 0이다. v86 source SHA-256은 `63e5ee9c635ec85149f7abcaf3507698ff741768f43f892af200b6e40c91dfa2`다. 이로써 A02의 예약 source 86개가 모두 작성되었고, 이제 영역 전체 token·exact/fuzzy·5어절·조사·보일러플레이트·형식 감사 및 직접 교정 뒤 corpus 포장을 수행한다.

- A02 train 최종 확정(2026-09-08): v01~v86 source/corpus 86/86쌍·12,900 records를 포장했다. 최초 파일 평균 허용범위 이탈 52개는 상한 50개 의미 보존 압축과 하한 v03·v70 의미 보강으로 교정했고, token 교정 뒤 반복 5어절 82종·초과 assignment 90건은 76개 `text` 직접 재서술, 반복 4어절 도입부 1쌍은 1개 문장 직접 재서술로 모두 0이 됐다. ID·relations는 이 교정에서 변경하지 않았다.
- A02 수정 정본 감사(2026-09-09): 전체 563,258 tokens(+EOS), 평균 43.663411, 파일 평균 37.520000~45.600000으로 86개 모두 허용범위 PASS다. artifact·exact/normalized/primary+relation-set·5-word·4어절 도입부·통제 relation·hard 조사·비정상 문자·문장 반복·review debt 오류는 0이고, 내부 문자 TF-IDF cosine 0.72 이상 0쌍(최고 0.426295796), word-set Jaccard 0.60 이상 0쌍(최고 0.379310345)이다. 문자 최고값은 독립 scikit-learn 전수값 0.42629579574110477과 같은 pair에서 일치한다. 조사 경고 221건은 정상 명사 말음·단어 내부·정상 구문의 오탐으로 사람 검토했다.
- A01과 동일한 감사기 정정 및 정본 digest 산식을 적용했다. A02 source/corpus 개별 SHA는 종전 보고서와 86/86씩 모두 일치해 데이터 drift와 record 수정은 0건이다. 새 source-set digest는 `54d6e0e6f4ffc45b1a3a6a1e536d60f723f75a639eeed5d02f443a8a6c074b27`, corpus-set digest는 `e879848b045d92b59ab0a50e126bff716753f6e9ce2a51e661cb1ddc14f82a6e`다. checkpoint SHA-256은 A01 수정 entry를 반영한 `53898b28e550ed12697d6bff8eead70c8679020c72923efec1ec9d356ca5798f`이고 A02 source/corpus SHA 불일치 0이며 중앙 family 원장·Stage2 manifest 참조 SHA가 일치한다. 통합 보고서는 `../stage2_highdensity_dataset/audit_reports/TinyLM_Stage2_A02_ConditionalDependency_Train_Consolidated_Audit_2026-09-08.md`와 기계 부속에 보존한다. 다음 작업은 완성된 A03 source v01~v69 중 v01을 보호하고 v02~v28의 남은 길이 교정 및 v20 상한 교정을 수행하는 것이다.

- A03 train 최종 확정(2026-09-09): 중단 뒤 실제 파일 대조에서 v01~v69 source 69개가 이미 완결됐고, 작업원장 길이 교정 상세는 v29~v36까지만 남은 반면 v02~v28도 실파일에서는 교정 완료 상태임을 확인했다. 완료 source를 재생성하지 않고 정본 입력으로 보존했다. 최초 영역 기준선 318,244 tokens(+EOS), 평균 30.748213, 파일 gate 7/69, 반복 5어절 328종·초과 assignment 527건, 반복 4어절 도입부 10종에서 직접 길이·표현 교정을 거쳐 최종 396,177 tokens(+EOS), 평균 38.277971, 파일 gate 69/69로 닫았다.
- A03 최종 수정은 2건이다. `S2-A03-T-060:30`의 고유사 문장을 네 시점 비교 근거로 다시 썼고, 정본 포장기의 전역 uniqueness gate가 찾은 A02와의 primary 충돌 `S2-A03-T-009:51`을 `표본적재 뒤 임계판정`으로 한정하며 text를 직접 재작성했다. ID·relations 변경은 0건이다.
- 정본 문법 gate는 `이다`·`이며` 같은 서술격 연결형을 주격조사 오류로 오인하지 않도록 수정하고 8건 fixture로 확인했다. 변경 후 A01·A02 재실행 수치는 유지됐고 A03의 실제 조사 오류는 0건이다. A03 내부 문자 3~5-gram TF-IDF 최고 `0.659134406`은 독립 scikit-learn 값 `0.6591344063725723`과 일치하며 0.72 이상 0쌍, word-set Jaccard 최고 `0.571428571`이며 0.60 이상 0쌍이다.
- A03 source/corpus v01~v69 69/69쌍·10,350 records의 artifact·exact/normalized·primary+relation-set·5어절·4어절 도입부·통제 relations·hard 조사·비정상 문자·review debt·train/validation 누출과 예약 unseen relation-set 충돌은 모두 0이다. source/corpus set digest는 `1e7f92ef0031dd1b88fab3b1c2f134e5b78b6e0e3eaea31640ed2b3a0621ab7e` / `29ee8cd92d6236f4352e62d54ada11a3fc53c47c5b1bf964f23ac576cf1cc496`, 현행 checkpoint SHA-256은 `b2e0ccf3411e5b8d4f2a05b3a62641fefe96c480c4e0897b8d787b6a205eb1f0`이다. 통합 보고서는 `../stage2_highdensity_dataset/audit_reports/TinyLM_Stage2_A03_TemporalOrder_Train_Consolidated_Audit_2026-09-09.md`와 기계 부속에 보존한다.
- Stage2 train 우선순서의 현 재개점은 A04 `state_transition`의 `S2-A04-T-001~069`이다. A01 validation v02 이후는 A02~A06 train 전체 완결 뒤 진행한다.

세부 진행률·artifact SHA·다음 예약은 `TinyLM_Stage2_Stage10_Actual3M_Expansion_Work_Ledger_2026-09-02.md`를 우선한다. `audit_reports/TinyLM_Stage2_10_Actual3M_Authorized_Checkpoint_Audit_2026-09-02.md`는 초기 승인 checkpoint이고, 완료된 영역의 최신 판정은 각 Stage 영역별 통합 감사보고서를 우선한다.
