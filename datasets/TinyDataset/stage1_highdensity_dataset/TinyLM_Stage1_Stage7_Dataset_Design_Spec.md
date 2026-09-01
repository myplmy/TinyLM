# TinyLM Stage 1~Stage 7 데이터셋 설계서·확정 원장

- 문서 상태: 현행 설계·이력 정본
- 기준일: 2026-08-31 KST
- 대상 프로젝트: 약 100M 파라미터급 한국어 TinyLM curriculum
- 짝 문서: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`

이 문서는 특정 데이터셋의 설계 방향, token·record 배분, ID 범위, 미리 선정한 concept family, 생성·감사 이력, 확정 산출물과 수정 금지 범위를 보존하는 원장이다. 범용 생성·검증 규칙은 짝 문서인 작업지침서를 따른다. 새 작업은 두 문서를 모두 읽어야 하며, 상태가 충돌하면 **실제 파일 → 최신 감사 JSON → 이 설계서 → 작업지침서 → 과거 handoff** 순으로 판정한다.

## 1. 지침서 이관 범위와 무손실 매핑

2026-08-31 분리 전 작업지침서의 특정 이력은 다음 위치로 이관했다.

| 분리 전 지침서 범위 | 이 설계서 위치 | 이관 내용 |
|---|---|---|
| Stage 1~7 역할, Stage 1 3M mixture | §2~§3 | curriculum 역할·배분·영역별 목적 |
| Identity 현행 snapshot | §4 | 파일·record·ID·legacy 주의·family 누적 |
| Attribute train 현행 상태 | §5 | 목표량·v01~v31 family·감사 결과 |
| Attribute validation 확정 상태 | §6 | 목표량·family·unseen 해석·감사 결과 |
| Function train 목표·27개 예약표·감사 | §7 | 의미 범위·ID·family·분포·산출물 |
| Function validation 목표·3개 family·감사 | §8 | 분리 방식·분포·other 유형·산출물 |
| 수정 금지 구체 목록·현재 산출물 | §9~§10 | 보호 pattern·감사/빌더/원고 목록 |
| 새 세션 현재 재개 상태 | §11 | 완료·진행·다음 작업 상태 |
| Stage1 (4) 신규 설계·31개 예약표 | §12 | boundary schema·ID·family·상태 원장 |
| Stage1 (5)~(10) 신규 train 설계·97개 예약표 | §14~§20 | 신규 slug·ID·필수 관계·family·생성 상태 원장 |

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

Stage 2~7은 상위 역할만 확정되어 있다. token mixture, 파일 수, ID 체계, train/val 비율은 별도 승인 없이 만들지 않는다.

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
- 상태: 사용자 지시에 따라 전체 수정 금지.

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

정본 감사: `TinyLM_Stage1_Attribute_Train_v01_v31_Full_Audit_2026-08-30.json`, `TinyLM_Stage1_Attribute_Train_v18_v31_Final_Audit_2026-08-30.md`.

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

정본 감사: `TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json`, `TinyLM_Stage1_Attribute_Validation_v01_v04_Final_Report_2026-08-30.md`.

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

정본 감사: `TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json`, `TinyLM_Stage1_Function_Train_v02_v27_Final_Audit_2026-08-30.md`.

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

정본 감사: `TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json`, `TinyLM_Stage1_Function_Validation_v01_v03_Final_Report_2026-08-31.md`.

## 9. 수정 금지 정본 원장

- `stage1_(1)identity_high_density_*` 전체
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

```text
TinyLM_Stage1_Attribute_Train_v18_v31_Final_Audit_2026-08-30.md
TinyLM_Stage1_Attribute_Train_v01_v31_Full_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v01_v17_Legacy_Audit_Before_Fix_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v01_v17_Legacy_Audit_After_Fix_2026-08-30.json
TinyLM_Stage1_Attribute_Train_v18_v31_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Audit_2026-08-30.json
TinyLM_Stage1_Attribute_Validation_v01_v04_Final_Report_2026-08-30.md
tools/build_function_train.py
tools/build_function_train_v02_v27.py
tools/function_sources/v02.tsv ... v27.tsv
tools/audit_function_corpus.py
TinyLM_Stage1_Function_Train_v01_Audit_2026-08-30.json
TinyLM_Stage1_Function_Train_v01_Progress_Audit_2026-08-30.md
TinyLM_Stage1_Function_Train_v01_v27_Full_Audit_2026-08-30.json
TinyLM_Stage1_Function_Train_v02_v27_Final_Audit_2026-08-30.md
tools/function_validation_sources/v01.tsv ... v03.tsv
tools/build_function_validation.py
tools/audit_function_validation.py
TinyLM_Stage1_Function_Validation_v01_v03_Audit_2026-08-31.json
TinyLM_Stage1_Function_Validation_v01_v03_Final_Report_2026-08-31.md
tools/boundary_sources/v01.tsv ... v31.tsv
tools/build_boundary_train.py
tools/audit_boundary_corpus.py
TinyLM_Stage1_Boundary_Train_v01_v31_Full_Audit_2026-08-31.json
TinyLM_Stage1_Boundary_Train_v01_v31_Final_Audit_2026-08-31.md
tools/boundary_validation_sources/v01.tsv ... v04.tsv
tools/build_boundary_validation.py
tools/audit_boundary_validation.py
TinyLM_Stage1_Boundary_Validation_v01_v04_Audit_2026-08-31.json
TinyLM_Stage1_Boundary_Validation_v01_v04_Final_Report_2026-08-31.md
tools/build_stage1_relational_train.py
tools/audit_stage1_relational_train.py
tools/stage1_relational_sources/{partwhole,statechange,spatial,comparison,context,type_uncertainty}/vNN.tsv
tools/build_stage1_relational_validation.py
tools/audit_stage1_relational_validation.py
tools/assemble_stage1_5_10_audit_reports.py
tools/stage1_relational_validation_sources/{partwhole,statechange,spatial,comparison,context,type_uncertainty}/vNN.tsv
audit_reports/README.md
audit_reports/Stage1_(5-10)_CrossArea_Consolidated_Audit.md
audit_reports/Stage1_(5)_PartWhole_Consolidated_Audit.md
audit_reports/Stage1_(6)_StateChange_Consolidated_Audit.md
audit_reports/Stage1_(7)_Spatial_Consolidated_Audit.md
audit_reports/Stage1_(8)_Comparison_Consolidated_Audit.md
audit_reports/Stage1_(9)_Context_Consolidated_Audit.md
audit_reports/Stage1_(10)_TypeUncertainty_Consolidated_Audit.md
audit_reports/machine/TinyLM_Stage1_*_Train_*_Final_Audit_*.json
audit_reports/machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json
audit_reports/machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json
audit_reports/archive/<area>/... (과거 progress 감사·보고서)
```

과거 handoff의 v18 재작성 전 상태와 삭제 예정이던 continuity summary의 v17 누적은 역사적 기록이다. 현재 상태는 실제 파일과 위 최신 감사가 기준이다.

## 11. 현재 재개 상태

- Identity train/validation: 완료·수정 금지
- Attribute train v01~v31, validation v01~v04: 완료·수정 금지
- Function train v01~v27, validation v01~v03: 완료·수정 금지
- Stage1 (4) Boundary train v01~v31: 4,650 records 완료·감사 통과·수정 금지
- Stage1 (4) Boundary validation v01~v04: 600 records 완료·감사 통과·수정 금지
- Stage1 (5)~(10) train: §14~§20의 97개 family, 14,550 records 전체 완료·감사 통과·수정 금지
- Stage1 (5)~(10) validation: §21~§28의 13개 신규 family, 13 files·1,950 records 완료·감사 통과·수정 금지; 각 파일 18개, 전체 234개(12.00%)를 relation-set 일반화 slice로 확정
- 다음 미확정 Stage·validation은 사용자 승인과 별도 family 원장 없이 시작하지 않는다.

## 12. Stage1 (4) 개념 경계·반례 train 설계 원장

### 12.1 목표·schema·의미 경계

```text
Stage 1 영역: (4) 개념 경계·반례
전체 설계량: 420K
train 설계량: 약 378K
train 목표: 4,650 records = 31 files × 150
validation 예정량: 약 42K, 별도 사용자 지시 전에는 생성하지 않음
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

작업 시작 시 고정한 Identity·Attribute·Function train/validation 보호 파일 110개의 SHA-256은 종료 시 110/110 모두 일치했다. 다른 밀도의 데이터는 생성·중복 비교·감사 기준에서 제외했다. 파일별 SHA-256과 버전별 relation 분포는 `TinyLM_Stage1_Boundary_Train_v01_v31_Final_Audit_2026-08-31.md`와 기계 판독 정본 `TinyLM_Stage1_Boundary_Train_v01_v31_Full_Audit_2026-08-31.json`에 보존한다.

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

작업 시작 시 고정한 Identity·Attribute·Function train/validation, Stage2 Attribute 확정 파일, Boundary train 보호 파일 141개의 SHA-256은 종료 시 141/141 모두 일치했다. 다른 밀도와 held-out은 생성·중복 비교·감사 기준에서 제외했다. 상세 수치와 version별 relation 분포는 `TinyLM_Stage1_Boundary_Validation_v01_v04_Final_Report_2026-08-31.md`와 기계 판독 정본 `TinyLM_Stage1_Boundary_Validation_v01_v04_Audit_2026-08-31.json`에 보존한다.

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
