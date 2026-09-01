# TinyLM Stage 2~Stage 10 curriculum·concept-family 사전 예약 초안

- 상태: corpus 미생성, tokenizer pilot 전 잠정 예약
- 작성일: 2026-09-01 KST
- 정본 근거: `TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`, `TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`, 실제 Stage1 고밀도 구조
- 제외: 저밀도 `stage1_dataset`, held-out/benchmark, 다른 밀도 corpus

## 1. 제안 결론

각 Stage는 설계상 약 3M token을 목표로 하되 tokenizer가 정해지기 전에는 token을 실측값으로 부르지 않는다. Stage1 실제 고밀도는 255 files·38,200 records·2,886,573 text characters(평균 75.565자)이며, 새 250 files·37,500 records 안은 평균 80자일 때 3M **문자 proxy**가 되는 잠정 기준이다. 이는 tokenizer token 수가 아니다.

Stage당 primary 250 files·37,500 records를 예약한다. train 225 files·33,750 records, validation 25 files·3,750 records로 정확히 90:10이다. 90:10은 checkpoint 선택용 validation을 충분히 유지하고 150-record 단위를 지키므로 현 단계 권고안이다. 최종 blind held-out은 이 3M 밖에서 별도로 동결한다. 총량 안에 blind split까지 넣는 90/8/2 대안은 가능하지만 Guide의 경계를 바꾸므로 별도 승인이 필요하다.

| 항목 | Stage별 잠정값 | 지위 |
|---|---:|---|
| 설계 token | 약 3,000,000 | tokenizer 미실측 |
| Stage1 실측 참조 | 255 files / 38,200 records / 2,886,573자 | 문자 proxy |
| primary 전체 | 250 files / 37,500 records | 잠정 |
| train | 225 files / 33,750 records | 정확히 90% |
| val | 25 files / 3,750 records | 정확히 10% |
| contingency | 25 family, ID·version 없음 | 비활성 |
| 파일 단위 | 150 records | Guide 준수 |
| val 일반화 slice | 파일당 18 / 150 = 12% | relation-set 기준 |

## 2. tokenizer 보정 gate

각 Stage에서 교육 성격이 다른 A01-v01, A03-v01, A06-v01 train 3파일과 A01-v01 validation 1파일, 총 600 records를 먼저 직접 작성·감사한다. 실제 학습 tokenizer의 평균 token/record를 잰 뒤 `raw_files = round(3,000,000 / 평균 token/record / 150)`을 계산하고, 정확한 90:10을 유지하려면 `total_files = 10 × round(raw_files / 10)`으로 정규화한다.

측정 결과 파일이 부족하면 ID·version이 없는 contingency 25개 중 필요한 수만 사용자 승인 후 primary tail 뒤에 활성화한다. 파일이 과다하면 primary tail을 임의 삭제하지 않고 보류안을 승인받는다. pilot 전에는 record 수·문자 수를 token 수로 보고하지 않는다.

## 3. protected legacy Stage2 충돌 회피

Design §9의 `stage2_(2)attribute_high_density_*`는 현재 경로에 실제 파일이 없어도 완성·보호 pattern이다. 이 초안은 해당 파일을 읽어 3M mixture에 섞거나, 이름을 바꾸거나, 다시 생성하지 않는다. 새 Stage2의 curriculum area 번호 1~6은 교육 순서를 뜻하지만 실제 filename의 area slot은 `(11)`~`(16)`을 사용해 legacy `(2)attribute`와 번호 의미 충돌을 피한다. 이 namespace는 Design §29~§39와 중앙 원장에 등록을 마쳤으며, 실제 생성은 pilot·tokenizer 측정·배분 승인 gate 뒤에만 시작한다.

## 4. 공통 파일·ID·relation 규약

- 파일: `stageN_(M)<slug>_high_density_train_vNN.json`, `stageN_(M)<slug>_high_density_val_vNN.json`. Stage2의 M은 11~16, Stage3~10은 1~6이다.
- version: 영역별 v01부터 연속, 최대 v45라 두 자리 0-padding을 유지한다.
- ID: 영역·split별 고유 prefix와 5자리 번호를 사용한다. 예: `S2-CSH-00001`, `S2-CSV-00001`.
- packet: 아래의 `<slug>_packet`만 사용하며 새 slug·prefix는 Design에 등록한 뒤 생성한다.
- relation 통제 어휘는 `is_a`, `subclass_of`, `part_of`, `classification`, `boundary`, `contrast`, `comparison`, `function`, `role`, `process`, `state`, `attribute`, `other` 13개뿐이다. 한 record는 실제 text 의미에 맞는 2~5개를 중복 없이 쓴다. relation focus는 분포 강제가 아니다.
- validation은 train exact text, primary concept, primary+정렬 relation-set, 5어절 문구와 단순 paraphrase를 피한다. Stage별 val domain bank는 train bank와 분리했다.
- `unseen_relation: true`는 원칙적으로 train에 없던 정렬 relation-set 조합이며 파일당 18개(12%)다. 통제 어휘 밖 label을 만들지 않는다.
- 이 원장은 family·ID·version만 예약한다. corpus `text`, primary concept, record relation 배열은 생성하지 않았다.

## 5. Stage별 세부 교육영역

### Stage 2 — 복합 관계·의존·인과·조건 구조

조건부 관계, 원인–결과, 의존성, 가능성, 시간적 선후, 상태 전이와 다중 관계 조합을 분리·결합한다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 11 | 원인 구조 / `causal_structure` | 20% | 600,000 | 45/5 | `causal_structure_packet` | `S2-CSH` / `S2-CSV` | 원인·결과·매개·공통 원인을 개입과 관찰의 차이까지 포함해 판정한다. | 상관을 인과로 승격, 결과 뒤 사건을 원인으로 단정, 단일 원인 과장 |
| 2 / 12 | 조건·의존 구조 / `conditional_dependency` | 20% | 600,000 | 45/5 | `conditional_dependency_packet` | `S2-CDH` / `S2-CDV` | 필요조건·충분조건·선행 의존·예외 범위를 실제 결과와 분리한다. | 필요와 충분의 역전, 기본값을 무조건 규칙으로 확대, 의존 방향 반전 |
| 3 / 13 | 시간 순서·간격 / `temporal_order` | 16% | 480,000 | 36/4 | `temporal_order_packet` | `S2-TOH` / `S2-TOV` | 사건의 선후·동시성·기간·지연·관측 창을 구별한다. | 서술 순서를 사건 순서로 오독, 겹친 기간을 동일 시점으로 단정 |
| 4 / 14 | 상태 전이·동역학 / `state_transition` | 16% | 480,000 | 36/4 | `state_transition_packet` | `S2-STH` / `S2-STV` | 전이 전후 상태, 촉발·억제 조건, 중간 상태와 가역성을 연결한다. | 상태를 정체성으로 고정, 중간 상태 생략, 가역·비가역 혼동 |
| 5 / 15 | 가능성·양상 / `modality_possibility` | 16% | 480,000 | 36/4 | `modality_possibility_packet` | `S2-MPH` / `S2-MPV` | 가능·예정·예측·확률·확신·반사실을 실제 발생과 분리한다. | 가능성을 사실로 승격, 계획과 예측 혼동, 확신을 확률로 치환 |
| 6 / 16 | 다중 관계 조합 / `relational_composition` | 12% | 360,000 | 27/3 | `relational_composition_packet` | `S2-RCH` / `S2-RCV` | 여러 객체와 관계를 다단 연결하면서 충돌·누락·우선순위를 보존한다. | 한 관계를 전체 경로에 전이, 국소 사실로 전역 결론, 충돌 정보 은폐 |

- train 객체·상황 bank(9): 스마트 온실 관수·환경제어, 도시 상수도 정수·배수 운영, 클라우드 서비스 부하·장애 대응, 철도 운행 간격·환승 조정, 하천 저수지 수위·방류 관리, 식품 냉장 유통·품질 유지, 온라인 학습 진도·피드백 운영, 생태 복원지 종·서식지 관찰, 배터리 저장장치 충방전·열관리
- val 신규 객체·상황 bank(5): 문화재 수장고 온습도·보존 운영, 양봉 군체 활동·질병 관리, 해저 통신케이블 장애·복구, 공연장 입장·좌석·대피 운영, 고산 구조대 탐색·후송 상황
- pilot: `S2-A01-T-001`, `S2-A03-T-001`, `S2-A06-T-001`, `S2-A01-V-001`
- contingency domain(5): 지하철 역사 환기·혼잡 제어, 수산 양식장 수질·급이 운영, 태양광 발전소 출력·고장 관리, 응급 콜센터 배차·인계, 도심 빗물저류·침수 대응

### Stage 3 — 절차·행동·계획·문제 해결

목표, 계획, 단계, 제약, 자원, 선택, 우선순위, 실패와 복구를 행동 전후 상태와 연결한다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 목표·행동 연결 / `goal_action` | 20% | 600,000 | 45/5 | `goal_action_packet` | `S3-GAH` / `S3-GAV` | 명시 목표와 하위 목표, 행동 수단과 결과 상태를 연결한다. | 행동 자체를 목표로 오독, 수단과 성과 동일시, 부수 효과 누락 |
| 2 / 2 | 절차·순서 / `procedure_sequence` | 20% | 600,000 | 45/5 | `procedure_sequence_packet` | `S3-PSH` / `S3-PSV` | 선행조건과 단계 순서, 병렬 가능 단계, 확인 지점을 구조화한다. | 단계 누락, 순서 임의 교환, 병렬·직렬 혼동 |
| 3 / 3 | 계획 분해 / `planning_decomposition` | 16% | 480,000 | 36/4 | `planning_decomposition_packet` | `S3-PDH` / `S3-PDV` | 큰 목표를 검증 가능한 작업과 의존성으로 분해하고 재계획한다. | 과도하게 큰 작업, 의존 누락, 계획과 실행 로그 혼동 |
| 4 / 4 | 제약·자원 / `constraint_resource` | 16% | 480,000 | 36/4 | `constraint_resource_packet` | `S3-CRH` / `S3-CRV` | 시간·용량·권한·안전 제약과 소모·재사용 자원을 구분한다. | 희망사항을 제약으로 오독, 자원 중복 계산, 안전 제약 완화 |
| 5 / 5 | 선택·우선순위 / `decision_priority` | 16% | 480,000 | 36/4 | `decision_priority_packet` | `S3-DPH` / `S3-DPV` | 여러 대안의 비용·효용·위험·가역성을 기준에 맞춰 선택한다. | 한 축 우위를 전체 우위로 확대, 매몰비용 고착, 기준 변경 은폐 |
| 6 / 6 | 실행 감시·실패 복구 / `execution_recovery` | 12% | 360,000 | 27/3 | `execution_recovery_packet` | `S3-ERH` / `S3-ERV` | 진행 상태, 실패 징후, 재시도·롤백·우회와 종료 판단을 연결한다. | 실패를 성공으로 보고, 무한 재시도, 복구 뒤 검증 생략 |

- train 객체·상황 bank(9): 목공 가구 제작, 실험실 시료 분석, 지역 축제 운영, 전자상거래 창고 출고, 소프트웨어 릴리스, 산불 초기 대응, 다도시 여행 일정, 밭작물 파종·관개, 외래 진료 예약·검사
- val 신규 객체·상황 bank(5): 수중 다큐멘터리 촬영, 고문서 복원 작업, 드론 지형 측량, 이동식 급식소 운영, 천체 관측 캠페인
- pilot: `S3-A01-T-001`, `S3-A03-T-001`, `S3-A06-T-001`, `S3-A01-V-001`
- contingency domain(5): 유리공예 제작, 이동형 도서관 운영, 해양 시료 채취, 야외 음악회 운영, 소형위성 조립

### Stage 4 — 문맥·담화·지시·대화

장문 참조, 생략, 대화 상태, 질문–응답, 지시 추적, 화행, 암시와 맥락 의존을 다룬다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 담화 지시·참조 / `discourse_reference` | 20% | 600,000 | 45/5 | `discourse_reference_packet` | `S4-DRH` / `S4-DRV` | 명사구·대명사·지시어의 선행 대상을 거리와 담화 중심 변화 속에서 추적한다. | 가까운 명사를 무조건 선행사로 선택, 화제 전환 누락 |
| 2 / 2 | 생략·공동지시 / `ellipsis_coreference` | 20% | 600,000 | 45/5 | `ellipsis_coreference_packet` | `S4-ECH` / `S4-ECV` | 한국어 생략 성분과 반복 명칭의 동일·비동일 대상을 문맥으로 복원한다. | 주어·목적어 임의 보충, 같은 표현을 같은 객체로 자동 합치기 |
| 3 / 3 | 대화 상태 / `dialogue_state` | 16% | 480,000 | 36/4 | `dialogue_state_packet` | `S4-DSH` / `S4-DSV` | 참여자 목표, 합의·미합의, 열린 질문, 약속과 수정 이력을 유지한다. | 철회된 합의를 유지, 미답 질문을 완료 처리, 화자 역할 혼동 |
| 4 / 4 | 질문–응답 적합성 / `question_answer` | 16% | 480,000 | 36/4 | `question_answer_packet` | `S4-QAH` / `S4-QAV` | 질문의 초점·범위·전제에 맞는 답과 미답·부분답·회피를 구분한다. | 관련 정보만 있으면 답으로 인정, 거짓 전제 수용, 범위 초과 |
| 5 / 5 | 화행·대화 행위 / `speech_act_pragmatics` | 16% | 480,000 | 36/4 | `speech_act_pragmatics_packet` | `S4-SPH` / `S4-SPV` | 진술·질문·요청·약속·경고·허가의 기능과 조건을 판정한다. | 문장형만으로 화행 결정, 권고를 명령으로 확대, 권한 누락 |
| 6 / 6 | 함축·맥락 의존 / `implicature_context` | 12% | 360,000 | 27/3 | `implicature_context_packet` | `S4-ICH` / `S4-ICV` | 말한 내용과 함축, 관례·공유 지식·상황에 의존한 해석을 분리한다. | 함축을 문자적 사실로 기록, 풍자·완곡 표현 과잉 확정 |

- train 객체·상황 bank(9): 심리상담 초기면담, 전자제품 고객지원, 과학 수업 토론, 설비 교대 일지, 프로젝트 의사결정 회의, 온라인 기사 정정과 댓글, 국제여행 안내 창구, 행정 민원 보완 대화, 협동 게임 팀 소통
- val 신규 객체·상황 bank(5): 고고학 구술 인터뷰, 국제회의 동시통역, 미술관 도슨트 문답, 선박 해상무선 교신, 지역사 구술채록 검증
- pilot: `S4-A01-T-001`, `S4-A03-T-001`, `S4-A06-T-001`, `S4-A01-V-001`
- contingency domain(5): 재난현장 브리핑, 항공관제 교신, 언어교환 수업, 생방송 인터뷰, 공동주택 주민회의

### Stage 5 — 일반화·추론·전이

귀납·연역 구조, 반례 기반 일반화, 새로운 개념 조합, 규칙·구조의 다른 도메인 전이를 다룬다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 귀납 일반화 / `induction` | 20% | 600,000 | 45/5 | `induction_packet` | `S5-INH` / `S5-INV` | 표본에서 규칙을 제안하되 범위·대표성·불확실성을 함께 유지한다. | 소표본을 보편 법칙으로 확대, 선택 편향·기저율 무시 |
| 2 / 2 | 연역 추론 / `deduction` | 20% | 600,000 | 45/5 | `deduction_packet` | `S5-DEH` / `S5-DEV` | 규칙·전제·조건에서 유효 결론을 도출하고 불충분 전제를 식별한다. | 결과 긍정·전건 부정, 암묵 전제 삽입, 양화 범위 오류 |
| 3 / 3 | 반례 기반 일반화 / `counterexample_generalization` | 16% | 480,000 | 36/4 | `counterexample_generalization_packet` | `S5-CGH` / `S5-CGV` | 반례가 규칙 전체·범위·조건 중 무엇을 수정하는지 판정한다. | 예외 하나로 모든 경향 폐기, 반례를 무시, 조건을 사후 부착 |
| 4 / 4 | 새 조합 일반화 / `compositional_novelty` | 16% | 480,000 | 36/4 | `compositional_novelty_packet` | `S5-CNH` / `S5-CNV` | 학습한 개념·관계를 새로운 조합에 적용하되 구성 요소 역할을 보존한다. | 함께 등장한 개념 동일시, 한 구성의 관계를 다른 구성에 복사 |
| 5 / 5 | 유추 전이 / `analogical_transfer` | 16% | 480,000 | 36/4 | `analogical_transfer_packet` | `S5-ATH` / `S5-ATV` | 표면 유사성과 구조 대응을 구분하고 대응 가능한 관계만 전이한다. | 어휘 유사성만으로 전이, 관계 대응 뒤 속성까지 무조건 복사 |
| 6 / 6 | 도메인 구조 전이 / `structural_transfer` | 12% | 360,000 | 27/3 | `structural_transfer_packet` | `S5-STH` / `S5-STV` | 한 도메인의 규칙·제약·계층을 다른 도메인에 적용하고 불변·변경 요소를 표시한다. | 도메인 고유 제약 누락, 명칭만 바꾼 모사, 단위·척도 무시 |

- train 객체·상황 bank(9): 신소재 내구성 시험, 작물 품종 수확량 분석, 야생동물 개체군 조사, 검색 알고리즘 성능 평가, 대중교통 수요 변화, 지역 전력 사용 예측, 방언 변화 자료 분석, 소액대출 위험 분석, 제조 공정 불량 분석
- val 신규 객체·상황 bank(5): 산호초 회복 조사, 필사본 연대 추정, 외계행성 후보 분류, 전통 유약 소성 분석, 도시 열섬 완화 평가
- pilot: `S5-A01-T-001`, `S5-A03-T-001`, `S5-A06-T-001`, `S5-A01-V-001`
- contingency domain(5): 고래 음향자료 분석, 고대 동전 분류, 화산 가스 변화 예측, 농촌 인구 이동 분석, 로봇 파지 성능 시험

### Stage 6 — 지식 통합·장문맥·복합 문제

긴 문맥, 다단계 추론, 복합 제약, 다중 목표, 정보 통합과 불확실성 관리를 다룬다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 장문맥 유지 / `long_context` | 20% | 600,000 | 45/5 | `long_context_packet` | `S6-LCH` / `S6-LCV` | 긴 문서의 인물·객체·시점·정의·변경 이력을 압축 없이 유지한다. | 초반 사실 망각, 동명이인 합치기, 최신 정정 이전 정보 사용 |
| 2 / 2 | 다단계 추론 / `multihop_inference` | 20% | 600,000 | 45/5 | `multihop_inference_packet` | `S6-MHH` / `S6-MHV` | 흩어진 전제를 연결해 중간 결론과 최종 결론의 근거 경로를 보존한다. | 중간 단계 생략, 다른 경로의 전제 혼합, 결론 순환 |
| 3 / 3 | 복합 제약 만족 / `constraint_satisfaction` | 16% | 480,000 | 36/4 | `constraint_satisfaction_packet` | `S6-CSH` / `S6-CSV` | 동시 제약의 충돌·우선순위·완화 가능성을 판정해 가능한 해를 찾는다. | 일부 제약 누락, 선호와 강제 제약 혼동, 숨은 충돌 방치 |
| 4 / 4 | 다중 목표·절충 / `multiobjective_tradeoff` | 16% | 480,000 | 36/4 | `multiobjective_tradeoff_packet` | `S6-MTH` / `S6-MTV` | 상충 목표의 지표·가중·하한과 절충을 언어적으로 판단한다. | 단일 점수로 모든 목표 은폐, 하한 위반, 한 집단 효용만 최적화 |
| 5 / 5 | 다중 출처 통합 / `multisource_integration` | 16% | 480,000 | 36/4 | `multisource_integration_packet` | `S6-MIH` / `S6-MIV` | 출처별 범위·시점·신뢰도·중복·충돌을 판정해 통합한다. | 출처 수를 신뢰도로 대체, 최신성만으로 우위, 중복 증거 이중 계산 |
| 6 / 6 | 불확실성 관리 / `uncertainty_management` | 12% | 360,000 | 27/3 | `uncertainty_management_packet` | `S6-UMH` / `S6-UMV` | 미지·누락·측정오차·모델 불확실성을 구분하고 결정에 반영한다. | 모든 불확실성을 하나로 합치기, 미관측을 0으로 치환, 과잉 확신 |

- train 객체·상황 bank(9): 광역 재난 자원 배치, 다기관 환자 이송 조정, 국제 공급망 차질 대응, 대규모 소프트웨어 장애, 환경영향평가 통합, 복지정책 대안 검토, 복합건설 공정 조정, 다논문 연구근거 종합, 장기 법률사건 기록 통합
- val 신규 객체·상황 bank(5): 극지 탐사대 운영기록, 오페라 제작 전과정, 위성 발사 임무기록, 다년 고고학 발굴기록, 항만 준설 영향 검토
- pilot: `S6-A01-T-001`, `S6-A03-T-001`, `S6-A06-T-001`, `S6-A01-V-001`
- contingency domain(5): 산악 철도 대수선, 백신 공급 캠페인, 해상풍력 건설, 국가기록물 디지털화, 유역 가뭄 공동대응

### Stage 7 — 지시 수행·대화·실전 사용

명령 이해, 출력 형식 준수, 다턴 대화, 도구·프로토콜 확장, 안전과 불확실성 처리, 실전 task 수행을 다룬다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 지시·의도 해석 / `instruction_intent` | 20% | 600,000 | 45/5 | `instruction_intent_packet` | `S7-IIH` / `S7-IIV` | 명시 요구, 범위, 금지, 우선순위와 완료 조건을 정확히 추출한다. | 부수 설명을 명령으로 오독, 금지 누락, 범위 확대 |
| 2 / 2 | 출력 형식 준수 / `output_format` | 20% | 600,000 | 45/5 | `output_format_packet` | `S7-OFH` / `S7-OFV` | 스키마·순서·길이·언어·금지 형식을 의미 손실 없이 지킨다. | 내용은 맞지만 형식 위반, 필드 추가, 순서·개수 오독 |
| 3 / 3 | 다턴 대화 수행 / `multiturn_dialogue` | 16% | 480,000 | 36/4 | `multiturn_dialogue_packet` | `S7-MDH` / `S7-MDV` | 이전 결정·수정·미해결 질문·사용자 선호를 유지해 후속 행동을 정한다. | 취소된 요구 재사용, 새 지시로 전체 맥락 삭제, 확인 중복 |
| 4 / 4 | 도구·프로토콜 / `tool_protocol` | 16% | 480,000 | 36/4 | `tool_protocol_packet` | `S7-TPH` / `S7-TPV` | 도구 선택, 입력 검증, 결과 해석, 오류·재시도·권한 경계를 준수한다. | 도구 결과 조작, 실패를 성공으로 보고, 권한 없는 실행 |
| 5 / 5 | 안전·불확실성 처리 / `safety_uncertainty` | 16% | 480,000 | 36/4 | `safety_uncertainty_packet` | `S7-SUH` / `S7-SUV` | 위험도, 권한, 가역성, 불확실성에 따라 질문·보류·거절·안전 대안을 선택한다. | 불확실한 고위험 행동 실행, 저위험 과업 과잉 거절, 권한 추정 |
| 6 / 6 | 실전 task 완결 / `practical_task` | 12% | 360,000 | 27/3 | `practical_task_packet` | `S7-PTH` / `S7-PTV` | 계획·실행·검증·보고를 연결해 실제 산출물의 완료 상태를 판정한다. | 준비를 완료로 보고, 검증 생략, 사용자에게 결과 위치 미고지 |

- train 객체·상황 bank(9): 보고서 형식 변환, 표 데이터 정제, 회의 일정 조율, 소프트웨어 변경 검토, 창고 재고 조정, 여행 예약 변경, 실험실 안전 절차 수행, 고객 문의 처리, 건물 대피 훈련
- val 신규 객체·상황 bank(5): 유물 보존 점검표 실행, 스포츠 대회 운영 프로토콜, 지역 라디오 방송 편성, 임시진료소 접수 흐름, 천문관 공개관측 행사
- pilot: `S7-A01-T-001`, `S7-A03-T-001`, `S7-A06-T-001`, `S7-A01-V-001`
- contingency domain(5): 법원 서류 제출, 학교급식 알레르기 대응, 공유자전거 정비, 전시회 발권 운영, 해안 정화 자원봉사

### Stage 8 — 평가·비판·검증·수정

Stage7의 실행 결과를 근거 품질, 오류, 논증, 검증, 수정과 확신 보정의 관점에서 독립 평가한다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 근거 품질 / `evidence_quality` | 20% | 600,000 | 45/5 | `evidence_quality_packet` | `S8-EQH` / `S8-EQV` | 주장별 근거의 직접성·독립성·범위·시점·측정 한계를 평가한다. | 근거 수를 품질로 대체, 인용 존재만으로 주장 확정, 간접 근거 과장 |
| 2 / 2 | 오류 탐지 / `error_detection` | 20% | 600,000 | 45/5 | `error_detection_packet` | `S8-EDH` / `S8-EDV` | 사실·논리·계산·범위·일관성 오류를 유형과 영향으로 식별한다. | 이견을 오류로 취급, 표면 오탈자만 고침, 연쇄 영향 누락 |
| 3 / 3 | 논증 비판 / `argument_critique` | 16% | 480,000 | 36/4 | `argument_critique_packet` | `S8-ACH` / `S8-ACV` | 주장·전제·근거·보증·반론 구조를 복원하고 가장 약한 연결을 평가한다. | 결론 불호를 논증 실패로 대체, 숨은 전제 방치, 반론 왜곡 |
| 4 / 4 | 검증·재현 / `verification_validation` | 16% | 480,000 | 36/4 | `verification_validation_packet` | `S8-VRH` / `S8-VRV` | 명세·테스트·독립 계산·교차 확인으로 주장을 재현 가능하게 검증한다. | 테스트 통과를 전체 정당성으로 확대, 같은 계산을 독립 검증으로 오인 |
| 5 / 5 | 수정·교정 / `revision_correction` | 16% | 480,000 | 36/4 | `revision_correction_packet` | `S8-RCH` / `S8-RCV` | 오류 원인과 영향 범위를 최소 수정으로 교정하고 재검증한다. | 증상만 덮기, 정답까지 변경, 수정 뒤 회귀검사 누락 |
| 6 / 6 | 확신 보정·유보 / `calibration_abstention` | 12% | 360,000 | 27/3 | `calibration_abstention_packet` | `S8-CAH` / `S8-CAV` | 증거 강도에 맞춰 확신·조건부 답·추가 확인·판단 유보를 선택한다. | 근거 없는 단정, 모든 불확실성에 회피, 정확도와 확신 혼동 |

- train 객체·상황 bank(9): 과학 실험 보고서, 공공 데이터 대시보드, 정책 효과 메모, 소프트웨어 변경안, 탐사보도 기사, 설비 고장 진단서, 언어모델 응답, 법률 논증서, 교육 평가 문항
- val 신규 객체·상황 bank(5): 박물관 소장 이력 보고, 야생동물 카메라 판독, 오케스트라 리허설 기록, 지질도 해석 보고, 식품 관능평가 결과
- pilot: `S8-A01-T-001`, `S8-A03-T-001`, `S8-A06-T-001`, `S8-A01-V-001`
- contingency domain(5): 임상지침 요약, 특허 신규성 검토, 교량 안전점검, 금융 공시 검토, 번역 품질 검토

### Stage 9 — 연구·도구 오케스트레이션·지속 워크플로

다중 출처 조사, 여러 도구, 장기 상태, 협업 인계, 모니터링과 출처 감사를 하나의 지속 workflow로 운영한다.
Stage8의 검증 능력을 장기 조사·도구·협업 workflow에 적용하는 층이다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 조사·종합 / `research_synthesis` | 20% | 600,000 | 45/5 | `research_synthesis_packet` | `S9-RSH` / `S9-RSV` | 질문을 검색 가능한 하위 문제로 나누고 다중 출처를 비교해 출처 있는 종합을 만든다. | 검색 결과 나열, 출처 충돌 은폐, 인용과 추론 혼합 |
| 2 / 2 | 도구 오케스트레이션 / `tool_orchestration` | 20% | 600,000 | 45/5 | `tool_orchestration_packet` | `S9-TOH` / `S9-TOV` | 여러 도구의 입력·출력·의존성·실패를 계획하고 결과를 연결한다. | 도구 순서 역전, 중간 결과 미검증, 실패 출력 재사용 |
| 3 / 3 | 워크플로 상태 지속 / `workflow_state` | 16% | 480,000 | 36/4 | `workflow_state_packet` | `S9-WSH` / `S9-WSV` | 장기 작업의 완료·진행·대기·차단 상태와 산출물 버전을 보존한다. | 계획을 완료로 표시, 중단 뒤 중복 실행, 오래된 산출물 사용 |
| 4 / 4 | 협업·인계 / `collaboration_handoff` | 16% | 480,000 | 36/4 | `collaboration_handoff_packet` | `S9-CHH` / `S9-CHV` | 역할·권한·결정·미해결 항목·산출물을 다른 작업자에게 무손실 인계한다. | 책임 불명, 결정과 제안 혼동, 미실행 항목 누락 |
| 5 / 5 | 모니터링·적응 / `monitoring_adaptation` | 16% | 480,000 | 36/4 | `monitoring_adaptation_packet` | `S9-MAH` / `S9-MAV` | 관측 지표와 임계 조건을 바탕으로 기다림·알림·재계획·중단을 선택한다. | 변화 없는 상태를 실패로 오인, 과도한 polling, 기준 없는 재계획 |
| 6 / 6 | 출처·감사 가능성 / `provenance_audit` | 12% | 360,000 | 27/3 | `provenance_audit_packet` | `S9-PAH` / `S9-PAV` | 데이터·결정·변경·도구 결과의 계보와 재현 증거를 유지한다. | 출처 누락, 생성물과 원본 혼동, 실행하지 않은 검증 보고 |

- train 객체·상황 bank(9): 학술 조사 프로젝트, 소프트웨어 배포 프로그램, 하천 현장조사 캠페인, 공공조달 절차, 보안사고 대응, 다매체 콘텐츠 제작, 내부통제 감사, 지역복지 프로그램, 데이터센터 이전
- val 신규 객체·상황 bank(5): 남극 보급 운영, 독립영화제 운영, 습지 복원 협업, 전파망원경 유지보수, 난민지원 거점 운영
- pilot: `S9-A01-T-001`, `S9-A03-T-001`, `S9-A06-T-001`, `S9-A01-V-001`
- contingency domain(5): 선거 관찰 임무, 오픈소스 학술대회, 산호 양묘장 운영, 비상 통신망 전개, 공공 지도 갱신

### Stage 10 — 통합 전문 수행·장기 안전 자율성

도메인 지식, 추론, 도구, 협업과 검증을 장기 목표 아래 통합하면서 적대적 조건과 안전 경계를 관리한다.
Stage1~9의 지식·추론·실행·검증을 고위험·장기·교차도메인 과업에 통합하는 종착 층이다.

| 교육# / 파일slot | 세부영역 / slug | 비율 | token 설계 | train/val files | packet | ID H/V | 교육목표 | 오류 억제축 |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 / 1 | 전문 지식 통합 / `expert_integration` | 20% | 600,000 | 45/5 | `expert_integration_packet` | `S10-EIH` / `S10-EIV` | 여러 전문 영역의 정의·증거·제약·실행 기준을 충돌 없이 통합한다. | 한 도메인 기준을 타 도메인에 강제, 전문 용어 동형이의 혼합 |
| 2 / 2 | 교차 도메인 종합 / `crossdomain_synthesis` | 20% | 600,000 | 45/5 | `crossdomain_synthesis_packet` | `S10-CSH` / `S10-CSV` | 서로 다른 도메인의 구조를 대응시켜 새 해결안을 만들고 전이 한계를 검증한다. | 표면 비유를 해법으로 채택, 도메인 고유 위험 누락, 단위 불일치 |
| 3 / 3 | 장기 계획·자율 수행 / `long_horizon` | 16% | 480,000 | 36/4 | `long_horizon_packet` | `S10-LHH` / `S10-LHV` | 장기 목표를 단계·검증·승인·재계획으로 운영하며 상태를 지속한다. | 단기 성과로 최종 목표 완료 처리, 목표 표류, 승인 경계 초과 |
| 4 / 4 | 적대적·비정상 조건 강건성 / `adversarial_robustness` | 16% | 480,000 | 36/4 | `adversarial_robustness_packet` | `S10-ARH` / `S10-ARV` | 오염 정보, 기만, 분포 변화, 복합 실패 아래 핵심 불변조건을 지킨다. | 권위 있는 형식의 거짓 수용, 단일 신호 의존, 공격과 단순 오류 혼동 |
| 5 / 5 | 안전 자율성 / `safe_autonomy` | 16% | 480,000 | 36/4 | `safe_autonomy_packet` | `S10-SAH` / `S10-SAV` | 위험·권한·가역성·감독 가능성에 맞춰 자율 실행과 인간 승인을 배분한다. | 목표를 이유로 권한 확대, 불가역 행동 무승인 실행, 안전과 성과 상충 은폐 |
| 6 / 6 | 메타인지·자기통제 / `metacognitive_control` | 12% | 360,000 | 27/3 | `metacognitive_control_packet` | `S10-MCH` / `S10-MCV` | 자신의 지식·계획·검증 한계를 점검하고 추가 탐색·수정·유보를 선택한다. | 자기평가를 증거로 간주, 동일 방법 반복, 비용 없는 무한 검증 |

- train 객체·상황 bank(9): 연안 기후적응 전략, 지역 공중보건 계획, 스마트도시 전환, 자율실험실 연구, 분산에너지 전환, 국가 사이버방어, 성인교육 체계개편, 심우주 탐사 임무, 대지진 장기복구
- val 신규 객체·상황 bank(5): 문화재 반환 협상, 해양 탄소 관측망, 달 표면 거주기지, 감염병 기록 아카이브, 국제하천 공동관리
- pilot: `S10-A01-T-001`, `S10-A03-T-001`, `S10-A06-T-001`, `S10-A01-V-001`
- contingency domain(5): 인공지능 보건 거버넌스, 초국경 식량안보, 궤도 잔해 완화, 초대형 가뭄 적응, 디지털 공공인프라

## 6. family 원장 사용법

primary 2,250개 row는 `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json`의 `reservations`에 있다. 각 family는 한 개 150-record 파일만 담당한다. 이름은 `Stage–영역–split–순번: 객체·상황 domain — 의미 축`으로 고정했다. domain과 의미 축은 사람이 선정했고 자동 처리는 version·ID range·filename 포장에만 사용했다. 실제 corpus에서 family 이름·순서를 임의 변경하지 않는다.

추가 225개는 `contingency_reserve_families`에 있으며 Stage당 25개다. 이들은 exact family만 예약되었고 ID, version, filename이 없다. pilot에서 token 부족이 실측되고 사용자가 활성화를 승인할 때만 primary tail 뒤에 번호를 부여한다.

## 7. 생성 전후 gate

1. Design §29~§39와 중앙 원장에 등록된 slug·prefix·Stage2 11~16 slot 및 예약 family가 현행 정본과 일치하는지 확인한다.
2. Stage별 3 train+1 val pilot을 record별 직접 작성한다. family domain×의미 축은 topic 경계이지 문장 template가 아니다.
3. 실제 tokenizer token 수를 측정하고 3M 목표 대비 총 file 수를 재산정한다.
4. 90:10, 150 records, ID 연속성, 영역 비중을 보존한 tail 보류·reserve 활성화안을 승인받는다.
5. validation은 train corpus를 실측한 뒤 12% unseen 정렬 relation-set을 설계한다.
6. Guide의 JSON/UTF-8/schema/ID/relation/중복/5어절/유사도/조사/leakage/SHA 감사를 전수 수행한다.

## 8. 예약 원장 자체 감사

아래 수치는 원장 생성 직후 실제 파일을 다시 parse해 확인한다.

| 검사 | 기대·확인값 |
|---|---:|
| JSON parse | PASS |
| primary reservation rows | 2,250 |
| primary train / val rows | 2,025 / 225 |
| contingency reserve rows | 225 |
| Stage별 primary | 250 × 9 |
| Stage별 train / val | 225 / 25 |
| Stage별 records | 33,750 / 3,750 = 90/10 |
| Stage별 영역 비율 합 | 100% |
| reservation ID / filename / primary family exact 중복 | 0 / 0 / 0 |
| 정규화 primary family(domain+axis) 중복 | 0 |
| primary–reserve 및 reserve 내부 exact 중복 | 0 |
| 정규화 primary–reserve overlap / reserve 내부 중복 | 0 / 0 |
| Stage별 train–val exact domain overlap | 0 |
| controlled relation vocabulary 크기 | 13 |
| val unseen 목표 | 18/file, 12.00% |
| corpus text 생성 | 0 |
| 물리 JSON line 수 | 4,646 |
| JSON SHA-256 | `823881a7d7074d2c5e3c54a9c732262004ddabf7b4fade75825a963a58346c99` |
| relation focus의 통제 어휘 밖 값 | 0 |
| contingency의 ID/version/filename 부여 | 0 |
| Stage2 신규 slot 11~16 위반 / legacy filename 충돌 | 0 / 0 |
| Unicode `\\uXXXX` escape | 0 |

실제 JSON parse와 전수 집계 결과가 위 기대값과 모두 일치했다. Stage 2~10은 각각 primary 250개(train 225, val 25), 37,500 records(33,750/3,750), 영역 비율 100%, contingency 25개다. 이 감사는 예약 metadata만 확인한 것이며 corpus text 품질이나 tokenizer token 수의 통과를 뜻하지 않는다.
