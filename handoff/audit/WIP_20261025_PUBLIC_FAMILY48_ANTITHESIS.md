공개 원천48쌍의 독립 반 검토 — 2026-10-25

제공된 [고정 판독본](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md)의588줄·48쌍을 전량 읽었다. 입력은52,338바이트이며 SHA256은 `86DB86E97A25BF02D4B92F9F54D4FDC4899D0C30F5DADB1B8D9A7D88BB90DD3F`다. 영어·한국어의 Dolly-v2, HotpotQA, SODA-inst에서 각각8쌍이다. 이 문서는 본문·질문·답의 의미 대조 의견이며 원천 전량의 오류율·가용 토큰·학습 적격 판정이 아니다.

원 parquet·각 가족의 번역 전 원문·adapter 코드·파생 학습 대화는 이번에 읽지 않았다. 외부 자료를 통한 독립 사실 확인도 수행하지 않았다. 따라서 아래의 정렬 성립은 질문이 요구하는 답 유형이나 제공 근거에 맞는다는 뜻이며 모든 배경사실이 참이라는 인증이 아니다. 정답 전체가 틀렸다는 판단과 표현 손상·낮은 정보량·원문 근거 미포함을 구분했다.

한영48쌍은 언어별로 따로 뽑힌 표본이다. 같은 행의 번역쌍이 아니므로 영어군에서 자연스러운 답이 있었다는 사실로 한국어군의 오역 지점을 입증할 수 없다. 영어 텍스트 자체의 무결성도 인증하지 않았다. source_family의 `(T)` 뜻은 이번에 확인하지 않았고 번역쌍 식별자로 사용하지 않았다. 명백한 결함도 이미 제공된 텍스트에 존재한다는 것까지 확인했으며, 원저자·상위 번역·표시 생성·현재 adapter 중 누가 만들었는지는 미분리다.

**군별 의견**

| 군 | 확인한 가치와 문제 | 일괄 보류하면 놓치는 점 |
|---|---|---|
| 영어 Dolly-v2 | 지문 추출·정의·분류·추천이 섞여 있다. 문 없는 삶의 논거, 목록 누락, 위험한 창작 용도 등은 개별 문제다. | 화물 회사 추출과 기본 정의처럼 요청과 직접 대응하는 쌍도 있다. 가족명만으로 같은 결함을 가정하면 안 된다. |
| 한국어 Dolly-v2 | 근거형 답의 핵심이 맞아도 근거의 용어·시점·추출 범위·설명 깊이가 손상된 경우가 있다. | 디지털 전환의 어색한 용어만으로 전자회로 근거와 답의 정렬까지 부정할 수 없다. X/Y 수학 변수도 사람 템플릿과 다르다. |
| 영어 HotpotQA | 인명·날짜·단체·배역 등 답 유형은 대체로 해석 가능하지만 연결 근거 문단은 없다. 불완전한 답 조각·순환적 질문·모호한 비교가 보인다. | 근거형 추론 자료로의 미완과 폐쇄형 지식 문답의 오답은 다르다. 근거 부재만으로 전량 거부하면 안 된다. |
| 한국어 HotpotQA | 고유명사의 일반어 번역 의심, 평서형 질문, 서로 다른 사건의 연도 혼동 위험이 보인다. |1980/1972와 명명/혼인 연도는 원 질문 대상을 복구하기 전 숫자 불일치만으로 오답 확정할 수 없다. |
| 영어 SODA-inst | 창작 확장·대본 생성·대화 요약이 섞여 있고 리터럴 줄바꿈이 보인다. 재구성의 세부 추가는 요약에서 별도 검토해야 한다. | PersonX의 실명 치환과 허구의 세부 추가는 창작에서 정상일 수 있다. 내부 화자를 실제 채팅 역할로 바꾸면 다른 오류가 생긴다. |
| 한국어 SODA-inst | X 인자 같은 템플릿 번역, 대상물 변경, 주제 실현 부족, 백조/천둥·고유명사 표현 손상 등이 보인다. | 모든 X나 새 이름이 오류는 아니다. 말투가 거칠다는 점과 질문·답이 다른 사건이라는 점도 나눠야 한다. |

**영어 Dolly-v2 — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [6804059](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:5) | 질문 초점 이탈·근거 없는 단정 | 문 없는 삶을 묻는데 자동문·문손잡이를 만지지 않는 이점을 예로 들어 문 사용과 손잡이 접촉을 섞는다. 건강 이득과 도시 접근에 따른 지수적 난도도 본문 근거가 없다. 가능하다는 결론 자체를 거짓으로 확정할 수는 없다. | 개별 답의 논거·단정 표현 재판독 후보다. 특이한 질문이라는 이유로 탈락시키지 않고 원답의 문제로 기록한다. |
| [6803233](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:20) | 정렬 성립 | Apache Spark를 데이터 공학·과학·학습용 다언어 실행 엔진으로 설명해 정의 질문에 직접 대응한다. 이 표본에서 역할·템플릿·누락 문제는 보이지 않는다. | 기본 정의 후보로 보존 가능하다. 제품 버전이나 최신 기능을 검증한 결과는 아니다. |
| [6803823](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:31) | 목록 완전성 주의 | 고체·액체·기체의 주요 대응은 통상적 조건에서 자연스럽다. 다만 입력의 xenon 중복은 하나로 합쳐졌고 gases 항목은 답에서 빠졌다. 중복을 묶는 것과 항목 누락은 구분해야 한다. | 개별 목록 대응을 검토한다. 혈액·커피가 혼합물이라는 이유나 온도 조건이 없다는 이유로 주요 분류까지 모두 오답 처리하지 않는다. |
| [6811302](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:44) | 정렬 성립·시점 한계 | 런던 관광 추천에 박물관·미술관·산책·유료 명소를 제시해 요청 장르와 맞는다. 입장료·관람 가능성·강에서 보이는 범위를 현재 사실로 독립 확인하지는 않았다. | 여행 추천 후보와 시점 의존 정보로 구분한다. 근거 문단이 없다는 이유만으로 열린 추천 요청을 불일치로 보지 않는다. |
| [6805331](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:55) | 제공 근거의 연도 추출 성립 | 근거에 표시된 산호섬의1857년을 답해 참조 문서와 연결된다. 다만 질문의 집필 연도와 근거의 작품 표기·출판 연도는 엄밀히 같은 사실이 아닐 수 있다. | 연도 추출 정렬은 보존하되 집필 시점까지 인증하지 않는다.1857을 즉시 오답으로 바꾸거나 다른 연도로 추정 교정하지 않는다. |
| [6799339](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:67) | 정렬 성립 | 데이터 접근성과 활용 교육을 함께 설명해 데이터 민주화의 의미를 묻는 요청에 대응한다. 하나의 유일한 사전 문구를 요구하는 질문은 아니다. | 정의·설명 후보로 보존 가능하다. 짧다는 이유만으로 의미 오류로 분류하지 않는다. |
| [6810603](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:78) | 원답의 개별 부적합 | 창의적 용도 다섯 개를 제시하지만 상해를 유도하는 용도가 불필요하게 포함된다. 자화한 프레임의 나침반 효용도 실제 사용 조건 없이 과장한다. 창작의 과장과 실용 보증은 다르다. | 일반 보조 답변용으로 원답 그대로 채택하기 어려운 개별 후보로 본다. 가족 전체 탈락이나 자동 위험어 필터의 근거로 확대하지 않는다. |
| [6801009](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:94) | 직접 추출 정렬 성립 | 지문에 나열된 화물 회사6개를 목록으로 추출하고 여객·통근 운영사를 섞지 않았다. 현재의 실제 운행 현황이 아니라 제공 지문에서 추출하는 과제다. | 근거형 추출 후보로 보존한다. 다른 Dolly 표본의 결함 때문에 이 쌍까지 함께 거부할 이유는 보이지 않는다. |

**영어 HotpotQA — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [1395157](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:111) | 핵심 답 정렬·답 조각 주의 | 공통 주류를 묻는 질문에 보드카라는 핵심은 들어 있다. 그러나 답 앞의 불완전한 서술 조각은 독립 답변의 완결성을 떨어뜨린다. 이를 보드카라는 사실 자체의 오답과 합치면 안 된다. | 개별 답의 문장 경계·원문 품질 확인 후보다. 문단 부재만으로 주류 사실을 오답 처리하지 않는다. |
| [1540580](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:122) | 답 유형 정렬·배경사실 미확인 | 배우를 묻고 George Timothy Clooney라는 인명을 답한다. 통칭보다 긴 이름이라고 다른 인물로 처리할 이유는 없다. 수상 횟수·원작 연결의 독립 근거는 제공되지 않는다. | 인물형 지식 문답 후보로 보존하되 배경사실 인증과 구분한다. 번역쌍이나 근거형 추론 완료로 세지 않는다. |
| [1379978](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:133) | 답 유형 정렬·배경사실 미확인 | 드라마 출연자의 밴드를 묻고 CNBLUE를 답해 목표 유형은 맞는다. 배우·기타 연주자·밴드 연결의 근거 문단은 없다. | 폐쇄형 지식 문답으로 검토할 수 있다. 연결 근거가 없는 상태와 질문·답이 틀렸다는 판정은 구분한다. |
| [1314082](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:144) | 날짜형 답 정렬·배경사실 미확인 | 특정 배우가 천재로 출연한 시리즈의 첫 방영일을 묻고 날짜를 답한다. 시리즈 이름과 출처는 표본에 없어 실제 연결의 전수 인증은 할 수 없다. | 날짜형 지식 문답 후보로 남긴다. 근거 문단 없음만을 일괄 탈락 사유로 쓰지 않는다. |
| [1342234](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:155) | 질문 설계·정보량 주의 | 영화·노예무역 설명 뒤 용어를 묻지만 답의 핵심인 노예제의 역사가 이미 질문에 들어 있다. 답 유형은 맞아도 복합 사실 추론 과제로서 새로운 연결이 약하다. | 얕은 정의·복사형 문답과 복합 추론 교육을 구분한다. 어색한 질문을 곧바로 다른 답과의 오정렬로 확정하지 않는다. |
| [1375328](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:166) | 답 유형 정렬·표현 주의 | 공연 관련 단체를 묻고 USO를 답한다. 문장의 연결 표현은 어색하지만 단체를 찾는 의도는 복원 가능하다. 실제 공연 관계의 외부 검증은 하지 않았다. | 개별 문장 품질과 사실 근거를 구분한다. 낯선 약어라는 이유만으로 정답을 일반어로 번역하지 않는다. |
| [1506838](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:177) | 답 유형 정렬·배경사실 미확인 | 영화 출연 배우가 해리 포터에서 맡은 배역을 묻고 Ginny Weasley를 답한다. 역할명으로 응답하는 구조는 맞지만 배우를 잇는 근거는 없다. | 배역형 문답 후보로 보존하며 실제 출연·배역의 인증과 구분한다. |
| [1262853](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:188) | 비교 기준 불명 | 두 잡지의 독자층이 비슷한지에 yes로 답하지만 성별·연령·국가 등 비교 기준을 명시하지 않는다. 긍정 자체가 거짓이라는 근거도 표본에는 없다. | 원래 비교 기준을 확인할 개별 후보다. 문단 없는 모든 yes/no 문답이 무효라고 확대하지 않는다. |

**영어 SODA-inst — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [11528827](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:199) | 창작 정렬·표시 서식 주의 | 하이킹 전제를 두 인물의 대본으로 확장해 요청과 맞는다. 갈림길·정상 전망 같은 새 세부는 창작에서 허용된다. 답에는 실제 줄바꿈 대신 리터럴 줄바꿈 표기가 보인다. | 대본 창작 후보로 보존한다. 서식의 발생 지점은 미확인이고 내부 화자를 실제 채팅 역할로 자동 분해하지 않는다. |
| [4140072](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:213) | 창작 정렬·과잉 성별 판정 주의 | 가방 수색이라는 사건을 유지하며 인물명·동기를 추가한다. him/he가 수색자, her가 가방 주인을 가리키면 지시가 일관될 수 있다. 이름의 통상 성별은 원문 조건이 아니다. | PersonX/Y의 실명 치환이나 표면 대명사만으로 오류를 확정하지 않는다. 인물 대응이 실제로 바뀌었다는 근거가 먼저다. |
| [3884792](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:227) | 창작 정렬 | 마지막 기회라는 주제를 인물의 사연으로 구체화한다. 질병·마지막 기회의 설정은 허구 속 인물의 진술이며 모든 진단이 임종이라는 의학 일반명제는 아니다. | 창작 후보로 검토한다. 민감한 소재가 등장하거나 전제보다 세부가 많다는 이유만으로 오답 처리하지 않는다. |
| [11301625](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:241) | 창작 정렬·표시 서식 주의 | 전자음악 축제라는 전제를 대화로 확장한다. 친구·장르·실제 가수 이름의 추가는 가상 대본의 설정일 수 있어 실제 축제 출연 사실 주장과 구분해야 한다. 리터럴 줄바꿈 표기가 있다. | 대본 창작 후보와 표시 서식 문제를 분리한다. 가상 출연진을 현실 일정의 거짓 정보로 곧바로 분류하지 않는다. |
| [10783098](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:255) | 원문 표현·재구성 범위 주의 | 대화 중 사람 이름이 음료명처럼 쓰이는 구절이 이미 있다. 답은 편안해졌다는 핵심을 반영하지만 병·알코올·목이 타는 감각은 대화에 명시되지 않는다. | 충실 요약의 정답으로 쓸지 창작적 서사 재구성으로 쓸지 구분한다. 이 새 세부를 사실로 보증하거나 adapter 오류로 단정하지 않는다. |
| [11645901](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:283) | 요약 핵심 정렬·표시 서식 주의 | 외출 금지 위반과 벌이라는 갈등이 답에 반영된다. 분노라는 감정은 추론이지만 대화와 양립한다. 입력의 리터럴 줄바꿈과 평탄한 화자 구분은 서식 문제다. | 요약 후보를 보존한다. 내적 인물의 성별·실제 채팅 역할을 임의 추정하거나 서식만으로 의미 전부를 거부하지 않는다. |
| [3681557](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:294) | 창작 정렬 | 숲 산책을 자연 관찰과 감정으로 확장해 주제에 맞는다. PersonX를 실명으로 바꾸는 것은 이 장르에서 가능한 변수 구체화다. | 명시적 이상이 없는 창작 후보로 남긴다. 새 나무·새소리·감정 묘사를 근거 없는 사실 추가와 동일시하지 않는다. |
| [2058936](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:308) | 창작 정렬·문체 선택 | 매력적인 목소리라는 주제를 비노골적인 호감 서술로 구체화한다. 새 이름·1인칭 화자는 창작의 선택이며 역할 교환의 증거는 아니다. | 목표 문체에 맞춰 개별 선별할 수 있다. 소재 단어나 PersonX만으로 자동 탈락시키지 않는다. |

**한국어 Dolly-v2 — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [1239430](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:322) | 시점 의존 지식 | 인구 수치를 직접 답하지만 기준 연도가 없다. 역사 시점의 수치일 수 있어 지금의 거짓 값으로 바로 판정하거나 현재 값으로 덮어쓸 수 없다. | 시점·원문 출처 확인 후보로 남긴다. 표본만으로 새 인구 수치를 제시하거나 전체 가족을 탈락시키지 않는다. |
| [1241398](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:333) | 정렬 성립·근거 번역 훼손 | 반복으로 진전 없는 대국을 끝내려는 취지의 답은 질문과 맞는다. 다만 근거의 조각·광장·지나가는 포착·승부차기와 <unk>는 체스 설명의 번역·표시 품질 문제다. 보장이라는 답 표현도 같은 근거의 선택적 무승부 주장과 구분해야 한다. | 질문·답 정렬과 근거 문장 품질을 따로 판독한다. 목적 설명을 즉시 전부 거짓으로 판정하거나 <unk>만 일괄 삭제해 해결됐다고 하지 않는다. |
| [1241392](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:345) | 정렬 성립 | 빅뱅 시점을138억 년 전으로 짧게 답해 질문에 직접 대응한다. 통상적 근사 표현이며 이 표본에 템플릿·역할 손상은 보이지 않는다. | 기본 지식 후보로 보존 가능하다. 짧다는 이유만으로 미완 답변으로 보지 않는다. |
| [1230011](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:356) | 번역 용어·문체 주의 | 건축 재료를 묻는 질문에 주요 재료와 지역 예를 답하지만 목록의 비석은 재료명과 완성 물체의 범주가 섞인 표현이다. 띄어쓰기·높임말도 고르지 않다. | 원재료 용어를 확인할 개별 후보로 본다. 원어를 읽지 않고 돌 등으로 추정 교정하거나 나머지 정렬까지 모두 부정하지 않는다. |
| [1241260](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:367) | 근거 정렬·용어 모호성 | 근거와 답 모두 전자 부품의 비선형성과 전자 흐름 제어를 연결한다. 디지털 전환은 전자 스위칭과 조직의 전환을 혼동시킬 수 있지만 질문에 붙은 근거가 전자회로 문맥을 준다. | 용어 번역 확인 후보다. 근거·답이 불일치한다고 단정하거나 그럴듯한 새 산업 설명으로 교체하지 않는다. |
| [1231180](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:379) | 정렬 성립 | 두 상품·두 소비자와 총량을 상자의 차원으로 설명해 에지워스 상자의 기본 정의를 묻는 질문에 대응한다. X/Y와 총량 기호는 의미 있는 수학 변수다. | 정의 후보로 보존한다. X가 들어 있다는 이유로 SODA의 손상된 사람 템플릿과 같은 대상으로 필터링하지 않는다. |
| [1233451](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:390) | 추출 범위·근거 밖 서술 문제 | 선수로 뛴 핵심 팀들은 답에 있지만 소유권·대회·야구 연도까지 확대한다. 야구를 불스 활동 중으로 묶는 표현은 근거의 은퇴→복귀 순서와 충돌하거나 모호하며 지문에서 직접 추출되지 않는다. | 질문이 요구한 팀명 범위와 추가 서술을 개별 재판독한다. 핵심 팀명이 맞는 것과 답 전체가 충실한 추출 견본인 것은 구분한다. |
| [1230193](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:402) | 열린 질문·설명 빈약 | 사랑의 이유에 특별한 느낌이라는 가능한 동기를 답하지만 설명이 빈약하다. 개인적·철학적 질문에 유일한 사실 정답이 있는 것은 아니다. | 내용 가치·설명 깊이 관점에서 낮게 선별할 수 있으나 사실 오답이나 adapter 오정렬로 확정하지 않는다. |

**한국어 HotpotQA — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [1485632](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:413) | 답 유형 정렬·배경사실 미확인 | 두 인물의 공통 직업을 시인으로 답하는 형식은 맞다. 다른 직업을 함께 가질 수 있으므로 한 인물이 소설가로 알려졌다는 이유만으로 공통 직업을 부정할 수 없다. 제공된 연결 근거는 없다. | 전기 사실 확인이 필요한 지식 후보다. 표본만으로 시인이 맞다고 인증하거나 틀렸다고 단정하지 않는다. |
| [1408572](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:424) | 고유명사 번역 손상 의심 | 약국 체인·매장을 묻는데 답이 롱스 마약이라는 일반명사형 표현이다. 약국 상호가 약물 일반어로 번역됐을 가능성이 크다. 실제 원 상호나 장소 사실은 이 표본만으로 확정하지 않았다. | 제공 답을 고품질 고유명사 정답으로 바로 채택하기 어렵다. 원문을 확인하기 전 상호를 추정 복원하지 않는다. |
| [1287404](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:435) | 질문 대상 연도 불명 | 질문에 승리의1980년이 있고 답은1972년이다. 상대의 타이틀 도전 연도를 물은 원문이 번역에서 흐려졌다면 두 연도는 다른 사건을 가리킬 수 있다. | 질문 대상·상대 사건을 확인할 개별 후보다.1972를 즉시 오답으로 판정하거나1980으로 바꾸는 것은 과잉 교정이다. |
| [1317362](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:446) | 질문 완결성 손상 | 지역이 행사를 개최했다는 평서형 문장에 동부 테네시라는 장소 답이 붙는다. 어느 지역인지 묻는 의도는 추정할 수 있지만 질문의 요구가 명시적으로 완결되지 않는다. | 누락된 질문 대상과 원문을 확인할 후보다. 장소 답 자체의 거짓이나 adapter의 필드 혼합으로 단정하지 않는다. |
| [1449553](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:457) | 질문·작품명 번역 주의 | 작품명과 역할·창시자의 연결이 어색한 평서형으로 제시된다. 답은 무술명 형태여서 가능한 목표와는 맞지만 원 작품명·배우·창시 관계의 근거는 없다. | 작품명과 질문 대상을 먼저 확인한다. 답 무술명을 임의 교체하거나 현재 번역을 사실 검증 완료로 올리지 않는다. |
| [1228784](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:468) | 선택지·답의 고유명사 대응 손상 | 밴드 두 개를 비교하는데 답 의학은 제시된 밴드 표기와 직접 대응하지 않는다. 같은 원 인명이 질문에서는 음역, 답에서는 일반어로 번역됐을 가능성이 있다. | 표면 불일치와 지리 사실을 분리한다. 원명 대조 전 다른 밴드가 정답이라고 고치거나 전체 지리 질문을 거부하지 않는다. |
| [1319066](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:479) | 선택지 정렬·분류 용어 주의 | 베로니카는 질문의 선택지와 대응한다. 다만 종이 더 많다는 문장에서 비교하는 분류군과 종 수의 시점·근거가 생략돼 있다. | 답 정렬을 보존하며 원 분류군·비교 근거의 확인 후보로 남긴다. 짧은 답과 낯선 식물명만으로 오역 확정하지 않는다. |
| [1276862](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:490) | 혼인 연도·명명 연도 혼동 위험 | 퀸즈버리의 명명과 여왕의 혼인 연도가 한 문장에 섞여 어느 해를 묻는지 모호하다. 답1761은 혼인 연도를 목표로 했을 가능성이 있어 지명 연도와 바로 비교하면 안 된다. | 원 질문의 연도 대상을 확인한다. 외부 지명 연도를 가져와 답을 자동 교체하거나1761을 즉시 거짓으로 확정하지 않는다. |

**한국어 SODA-inst — 8쌍**

| 표본·근거 위치 | 관측 | 판독 근거 | 의견·과잉 보류 경계 |
|---|---|---|---|
| [115918](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:501) | 사람 템플릿 번역·창작 정렬 | X 인자는 사람 변수의 번역으로 부자연스럽지만 친구 선택이라는 사건과 제넷·사라의 서사는 연결된다. 기존 친구 중 하나를 고르는 것이 불가능한 사건도 아니다. | 템플릿 표현을 확인할 후보로 남긴다. 이미 친구라는 설정이나 실명 치환만으로 모순·오정렬을 확정하지 않는다. |
| [300104](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:512) | 대상물 의미 불일치 | 질문은 대출에 대한 기록 반환이고 답은 빌린 책 반환이다. 제공 한국어의 대상물이 다르다. 원 record가 어떤 물체였는지, 번역 전부터 달랐는지는 알 수 없다. | 현재 쌍은 개별 의미 재판독 대상으로 둔다. 원문 확인 전 질문을 책으로 바꾸거나 답을 장부로 만들어 맞추지 않는다. |
| [472886](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:523) | 주제 정렬·번역·문체 주의 | 유방 임플란트를 얻는다는 주제는 유지하지만 사서 새로운 가슴의 주인이 된다는 표현은 절차와 소유를 거칠게 뭉개고 문체도 고르지 않다. 의료 조언을 요청하거나 제공하는 쌍은 아니다. | 창작 문장의 표현 품질을 개별 선별한다. 신체·의료 소재 단어만으로 가족 전체를 탈락시키지 않는다. |
| [106177](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:534) | 창작 정렬·템플릿 표현 주의 | 말을 잘하는 인물을 대화와 웃음으로 확장해 주제와 연결된다. X 인자라는 사람 지칭과 번역투·반복 표현은 품질 문제지만 별개 답이 붙었다는 증거는 아니다. | 의미 정렬과 문체를 나눠 검토한다. 새 인물·성격 추가를 창작 위반으로 처리하지 않는다. |
| [65569](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:545) | 주제 실현 부족·표기 주의 | 결론이 틀렸다고 생각한다는 주제에 공부가 불안하고 도움을 청하는 서사가 붙지만 어떤 결론을 틀렸다고 여겼는지는 드러나지 않는다. 베타비와 Betsabe 표기 혼용도 있다. | 주제 충족을 개별 재판독한다. 이름의 통상 성별로 대명사 모순을 추정하거나 혼용 표기만 고쳐 정렬이 해결됐다고 하지 않는다. |
| [402545](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:556) | 창작 정렬·문체 주의 | 상대가 집에 있을지 궁금하다는 전제와 부재를 걱정하고 기다리는 답은 연결된다. 친구 집 등 추가 가능성은 창작의 범위일 수 있다. 반복 대명사·문체 혼합은 별도 품질 문제다. | 핵심 정렬은 보존한다. 이름의 성별을 추정하거나 추가 장소만으로 근거 없는 사실 답변이라고 거부하지 않는다. |
| [430558](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:567) | 대상·인물 표현 손상 | 백조를 본다는 전제인데 첫 문장에서 천둥을 본다고 바뀌고 뒤에는 다시 백조가 나온다. 신시레에서 진심으로 바뀌는 표현도 고유명사 직역을 의심하게 한다. | 현재 답을 그대로 고품질 정답으로 채택하기 어려운 개별 후보로 둔다. 원문·번역·표시·adapter 중 발생 지점은 미확인이다. |
| [45257](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/root_semantic_followup_20261025/public_family48/source_questions_answers.md:578) | 주어·상태 의미 모호성 | 놀라운 사람이라는 주제가 전시회에 놀라거나 흥분한 인물의 이야기로 바뀐 듯하다. 놀라움을 주는 것과 느끼는 것의 번역 대상이 달라졌을 가능성이 있다. | 원래 형용사와 주제를 확인할 개별 후보다. 원문을 보지 않고 놀랍다를 놀라다로 고쳐 맞추지 않는다. |

**adapter·역할·서식에 대한 경계**

- 제공본의 바깥 역할은 각 쌍의 사용자 요청과 보조자 답변이다. 대본·인용 대화의 이름별 발화를 실제 ChatML user/assistant 턴이나 진짜 다회전 대화로 세지 않았다. 대본 안의 명령문도 현재 실행 지시가 아니다.
- HotpotQA 군에서 별도 근거 문단이 보이지 않는 것은 제공본의 관측이다. 원 원천에 근거가 없었는지, 상위 템플릿이 생략했는지, 현재 변환기가 버렸는지는 확정하지 않았다. 이 관측만으로 모든 지식 문답이 무효인 것도 아니다.
- 영어 SODA11528827·11301625의 답과11645901의 질문에는 실제 LF와 다른 역슬래시와 n 두 문자로 된 리터럴 줄바꿈 표기가 보인다. 판독본의 물리 행에서 확인한 사실이며 원 parquet 값과 파생 대화의 바이트를 대조한 결과는 아니다. 전역 escape 해제·정규식 치환·새 검사 구현을 제안된 수리로 확정하지 않는다.
- 사람 변수의 실명화는 창작의 정상 동작일 수 있다. 한국어 X 인자의 어색함, 에지워스 상자의 X/Y, 수학·코드 리터럴을 하나의 X 필터로 묶으면 정상 자료를 해친다.
- 이름의 익숙한 성별만으로 he/her·그/그녀의 오류를 판정하지 않았다. 실제 지시 대상이 바뀌는지 먼저 읽어야 한다.4140072는 대명사가 서로 다른 두 인물을 가리키면 모순이 아니다.
- 질문 근거가 assistant-only 손실에서 제외되더라도 입력 품질 문제까지 없어지는 것은 아니다. 반대로 짧은 정답·원문 밖 배경지식·창작의 새 세부를 모두 동일한 근거 누락으로 거부하면 과잉 보류다.
- 모든 표본의 권리는 상위 카드만을 기록한 `CARD_ONLY`다. 한국어의 `original_split`은 null이다. 이 사실은 즉시 불법·누출을 입증하지도, 원 가족의 권리·전역 문서 분할·편입을 통과시키지도 않는다. 원 split이 null이라는 이유만으로 source 경로의 train 이름을 검증된 전역 분할로 치환하지 않았다.
- `derived_nonpadding_tokens`와 `derived_targets`는 미측정이다. 표시된 원문 토큰을 더하거나 표본의 품질 의견을 이용해 A의 공급량·오류율·1024 적합량을 계산하지 않았다.

**총괄에게 남기는 의견**

제공된 형태에서 그대로 쓰기 어려운 개별 근거는 한국어 SODA300104의 대상물 불일치,430558의 대상 손상, HotpotQA1408572·1228784의 고유명사 표현, Dolly1233451의 추출 범위 확장 등이다.65569·45257·연도 질문들은 주제·대상을 다시 확인해야 하지만 올바른 원문을 추측해 바꾸면 안 된다. 이것은 이 사례들의 의견이며 모든 가족·언어에 적용할 자동 탈락 규칙이 아니다.

영어 Dolly6801009의 근거형 추출,6803233·6799339의 정의, SODA3681557의 창작 등에는 제공본에서 직접적인 오정렬 근거가 보이지 않는다. 이들을 보류 사례와 함께 버리거나 모든48개를 교사에게 다시 채점하게 하는 결론은 지지하지 않는다. 필요한 것은 확인된 개별 결함·자료 장르·원래 질문 대상을 구분하는 후행 판단이며 새 교사 재검수 체계의 구현이 아니다.

이번에는 지정 입력을 읽고 이 감사문서 한 파일만 작성했다. 코드·코퍼스·원로그·체크포인트는 변경하지 않았고 시험·GPU·학습·새 형식검사·자동 탈락·교사 실행은 하지 않았다. 전체 원천의 의미 감사 완료·학습 적격·75M 보충 완료를 주장하지 않는다.

