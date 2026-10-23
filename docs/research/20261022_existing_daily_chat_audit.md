# 2026-10-22 기존 세 모델 daily48 첫답 정성 감사

상태: `144_FIRST_ANSWERS_READ / DESCRIPTIVE_ONLY / NO_NEW_INFERENCE`.

지정된 `100439_daily48` 세 모델의 첫답을 각48개, 총144개 **전문 판독**했다. 31개 문자기대 진단과17개 수동 문항을 구분했고, 새로운 의미 정확도·긍정/부정 합계·모델 채택 판정은 만들지 않았다. 원자료·report의 자동 점수·기존 human-review 상태는 수정하지 않았다. 이번 쓰기는 이 문서 하나이며 새로운 코드·모델·훈련·GPU·CP 실행·다운로드·Git 작업은 없다.

## 1. 읽은 원형과 비교 범위

| 약호 | exact model | 지정 사람이 읽는 원답 | 대응 report / raw |
|---|---|---|---|
| F | native595-f | [review](/home/uranus/tinyLM/review_request/20261022_native595-f_100439_daily48.md) | [report](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/native595-f_100439/chat/report.json), [첫답 raw](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/native595-f_100439/chat/answers_000000.jsonl) |
| Q | native595-q | [review](/home/uranus/tinyLM/review_request/20261022_native595-q_100439_daily48.md) | [report](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/native595-q_100439/chat/report.json), [첫답 raw](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/native595-q_100439/chat/answers_000000.jsonl) |
| B | new595-broad-f | [review](/home/uranus/tinyLM/review_request/20261022_new595-broad-f_100439_daily48.md) | [report](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/new595-broad-f_100439/chat/report.json), [첫답 raw](/home/uranus/tinyLM/test_result/evidence/p106b_existing_probes_20261022/new595-broad-f_100439/chat/answers_000000.jsonl) |

[고정 fixture](/home/uranus/tinyLM/scripts/fixtures/p106b_daily_chat48_20261022.jsonl)의48행과 각 raw.source의48행이 ID·질문·language·category·expected_exact까지 순서대로 같음을 대조했다. raw shard bytes/행수/SHA를 manifest와, review 파일 SHA를 report와 대조했고, 각 review의48개 ID 절에 해당 질문과 답 전문이 그대로 있음을 확인했다. 아래 부록의 원형 행번호01~48은 **세 raw JSONL과 fixture의 실제1-based 행번호**와 같다.

세 report는 `CHAT_FIRST_ANSWERS_RECORDED_HUMAN_REVIEW_PENDING`, `strict_model_context_exit_verified=true`다. 기록된 조건은 FP32 MATH/TF32 OFF, greedy temperature0/top_k1, KV ON, MTP OFF, max_new96, first_answer_only=true, history=false다. 48개 각 ID의 기록된 prompt SHA도 세 모델에서 같다. 이는 동일 질문·프롬프트의 기존 결과 비교 근거이지, 세 모델의 학습 조건이나 학습된 함수가 같다는 뜻은 아니다.

| 모델 | report에 기록된 CP SHA256 | core SHA256 |
|---|---|---|
| F | `7DF60C47605B654520C510E2758D559213AABCB7ED1090424BDC0D50BC9413BA` | `E21E7023D5F289E2EBA2C65127491CB8016232A538E0619E63068BA095D4E3DD` |
| Q | `C0610452ABF357868DA1CCDF16D98482D408F2D9D076C634444292023108BDF5` | `C8F2A68232D95C8D4A8EDC455A5D389211806609C2F58E780C6EFF66E497F2DB` |
| B | `2630B4C2862A41CB677AC9CAA89B0F2DD03234C4FD540FCCA6205AA847CF1C71` | `00262611800E81BB117DB68F8053ED0A15A8454FBD9D34AFEFE44DB9A0D21B0D` |

공통 tokenizer SHA=`9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E`, ordered questions SHA=`C29500CC4CA223C66944BF64E243DE0910CF8DCE95D0456A8397EAFEB5EEBB8E`, fixture 실물 SHA=`4C177F0D467F81E50C723C327A2509A102D14E7FE53457920C8FADCD429A646B`다. CP와 tokenizer 파일 자체를 이번에 열거나 실행하지 않고 지정 report의 lineage만 읽었다.

## 2. 31문자기대와17수동 문항은 다른 분모다

각 모델의 기존 공백 정규화 완전일치 진단은 **0/31**이다. raw 진단의 규약은 공백 축약/strip만이며 대소문자·구두점·부호 등을 유지한다. 이것을 0/48 전체 대화 정확도나 의미상0/31로 바꾸지 않는다. 숫자·이름을 답에서 새로 추출하거나 alias를 새로 승인한 재채점도 하지 않았다.

fixture는 KO24/EN24지만 문자기대는 KO15/EN16, 수동은 KO9/EN8이다. 수동17개는 열린 설명8개만을 뜻하지 않는다. 조건 보존2개(`ko/en_logic_04`), JSON 형식2개(`ko/en_format_03`), 열린 설명8개(`ko/en_open_01..04`), 정보부족4개(`ko/en_info_01,03`), 한국어 가방색 문맥1개(`ko_info_04`)다. 특히 두 언어의 `info_04`는 비슷한 질문이지만 KO는 manual, EN은 `black` 문자기대라는 차이가 있다.

문자기대에서 맞는 문자열이 섞였다는 사실과, 문항을 올바르게 해결했다는 사실도 분리한다. 예를 들어 Q의 `ko_role_03`은 정확 첫문장 발췌로 **“수진은 지도를 만들었습니다.”**를 내고 같은 내용을 반복한다. 질문의 관계에 맞는 일부 내용이 있으나 이름만 한 번 쓰라는 형식과 종료를 지키지 않았다. 반대로 B의 `ko_format_01` 전문 **“1만 출력하세요.”**에서 숫자1을 임의 추출해 정답으로 바꾸면 지시문 재출력을 숨기게 된다.

## 3. 종료 관측과 답 품질은 별도다

| 모델 | MAX_NEW | STOP_SEQUENCE | EOS | 빈 문자열 | 기존 문자일치 |
|---|---:|---:|---:|---:|---|
| F | 45 | 0 | 3 | 0 | 0/31 |
| Q | 44 | 0 | 4 | 0 | 0/31 |
| B | 8 | 39 | 1 | 0 | 0/31 |

이 표는 원 report/raw의 기술적 관측이며 의미 성공/실패 합계가 아니다. F의 KO는 MAX_NEW21/EOS3, EN은24개 전부MAX_NEW다. Q의 KO는 MAX_NEW20/EOS4, EN은24개 전부MAX_NEW다. B의 KO는 STOP21/MAX2/EOS1, EN은 STOP18/MAX6이다. B가 이 원형에서 덜 길게 반복하며 더 자주 stop에 도달한다는 관측은 가능하지만, 짧게 종료한 `1`, `5`, `민수`, `B 상자`가 해당 질문의 정답이라는 뜻은 아니다. 실제 속도나 일반적인 종료 안정성으로도 확장하지 않는다.

F가 EOS로 끝난 `ko_logic_04` 전문은 **“A 상자는 빨강입니다.\n\n각주 \n\n대한민국의 음악”**이다. 올바른 색 관계와 무관한 후미가 함께 있다. Q의 `ko_open_02` EOS18답은 **“농구가 어떤 운동인지 어떻게든 하는가?\n\n각주 \n\n농구”**여서 EOS 자체가 설명 성공이 아님을 보여준다. B의 유일 EOS인 `ko_info_01`도 건물을 특정하는 대신 분류문구와 `luckiest`를 반복한다.

## 4. 과제별 실제 관측

### 4.1 산수: 식/문제 복제와 계산 결과 제출을 분리

한·영 `math_01`의 질문은1+1, 문자기대는2다. B는 두 언어 모두 전문 **“2+1”**을 내고 STOP으로 끝났다. `math_02`의2+2에는 양쪽 모두 **“2+2”**를 냈다. 후자는 계산 가능한 식을 되돌려준 것이지 요청된 숫자4 제출은 아니다. 이 감사에서 식을 계산해 대신 정답을 만들어 주지 않는다.

7개 사과 중3개를 먹는 `ko_math_03`에서 B는 **“1”**, `en_math_03`에서는 **“8 apples”**를 냈다. F/Q는 각각 사과 문장의 반복·과일의 일반 설명·`the number of people` 반복으로 이동한다. `math_04`의4×6에는 B가 한국어 **“2 곱하기 6의 값만 쓰세요.”**, 영어 **“5”**를 냈다. 질문 변경·오답·숫자만 지시 실패가 섞였고, 단순 alias 차이라고 볼 원답이 아니다.

### 4.2 대상/관계 결합: 관련 이름의 출현만으로는 부족

영어 사과 문맥 두 문항에서 B는 Jina17을 물으면 **“12 apples”**, 순서를 바꿔 Mina12를 물으면 **“17 apples”**라고 했다. 이 두 사례에서는 질의 대상보다 첫 수량을 따라가는 듯한 양상이 보이지만 이를 전체 문맥 전략으로 확정하지 않는다. 한국어 대응에서 B는 영희의 수량 질문에 **“민수”**를 내거나 숫자를17→18→20→21→22로 늘리며 반복한다.

`ko_role_03`/`04`는 같은 문맥에서 만든 사람/읽은 사람만 바꿨다. F의 두 답은 완전히 같은 `각주`·음악그룹 분류 반복이다. Q는03에서 수진이 만들었다는 맞는 일부 내용을 보이지만,04에서는 **“수진은 지도를 읽었습니다. 주진이 지도를 읽었습니다.”**(정확 접두 발췌)로 질의 관계를 틀린 대상에 붙인다. B는 각각 **“지도는 지도를 읽었습니다.”**, **“지도는 지도를 읽고 쓰는 사람입니다.”**라고 답했다. 영어에서도 F의 `en_role_03`에 Nora가 등장하더라도 **“Nora was a very good person.”**은 누가 그렸는지의 관계를 답한 문장이 아니다.

### 4.3 논리/조건 보존: 맞는 일부와 전제 변형을 구분

F의 영어 AND/OR 두 답은 전문이 서로 같다. B의 한국어 AND/OR는 둘 다 전문 **“A”**다. F/Q의 일부 답에는 `false`나 `거짓`이 반복되지만, 입력의A=true를A=false로 바꾸거나 다른 연산 문장을 내므로 단어 출현만으로 논리 성공을 판정하지 않았다.

한편 `ko_logic_04`에서 A빨강/B파랑 중 B만 초록으로 바뀌는 조건을 주면 F/Q는 A가 빨강이라는 문장을 내는 부분이 있다. F는 위의EOS 후미, Q는96token 반복이 뒤따른다. 영어 대응에서도 Q는 **“Box A is red and box A is red.”**를 반복해 A의 색 정보 자체는 보존한다. B는 한국어 **“B 상자”**, 영어 **“B is red and box B is blue.”**에서 시작하는 반복으로 물은 A를 놓친다. 이 대조는 B를 모든 답 유형의 의미상 승자로 부를 수 없게 한다.

여기서 `condition_update`는 한 user 질문 안에 처음/나중 조건이 함께 쓰인 **단일턴** 과제다. 실제 이전 턴 기억이나 대화 후속 수정 능력을 평가한 것이 아니다.

### 4.4 출력 형식: 정답 토큰 포함과 지시 준수는 다름

`ko_format_02`에서 Q는 `확인완료`가 들어간 질문 전체를 반복하고, B는 전문 **“열 확인완료 를 그대로 한 번만 출력하세요.”**를 낸다. `ko_format_04`에서 Q는 질문·각주 뒤에 `나`를 반복한다. 요구 글자를 담았다는 부분과 한 글자만 출력하는 형식 실패를 동시에 기록한다.

두 언어의 JSON 문항은 수동 문항이다. 세 모델 모두 해당 원답은 명령문·JSON 객체라는 문구·번호 나열을 반복하며 요구된 JSON 객체를 제출하지 않는다. 여기서는 새 JSON 자동 채점 점수를 만들지 않았다. B의 `en_format_02`도 **“- ready once again.\n”** 반복으로 `ready`만 한 번 출력하라는 요구를 충족하지 않는다.

### 4.5 열린 설명: B의 최소 관련 설명도 있고 유창한 무관 설명도 있음

B의 영어 농구 답(`en_open_02`) 전문은 다음과 같다.

> The sport of basketball is a sport that involves the use of a ball and a basket. It involves the use of a ball and a basket.

공·바스켓이라는 관련 핵심을 말한 최소 설명이다. 두 문장이 거의 반복이고 규칙·득점/팀 설명은 부족하지만, Native의 질문 재출력과 의미상 똑같다고 지워서는 안 된다. 반면 한국어 대응 B의 전문은 **“운동인지 처음 듣는 사람에게 설명해 주세요.”**로 질문 일부 재출력이다. 이 작은 대조를 영어 일반 능력 우세의 수치로 바꾸지는 않는다.

B의 영어 사과 답(`en_open_01`)은 과일/재배지를 말하는 두 문장이지만 같은 지역 문구를 반복하고 설명 범위가 좁다. 그 지역 진술의 진위까지 독립 인증한 것은 아니다. 폴더 정리 질문(`en_open_03`)에서는 유창한 bullet 형식으로 가다가 **“basic principles of folding”**, **“creating folds that are folded”**(각각 정확 부분 발췌)로 파일 정리의 이점이 아닌 다른 의미로 이동한다.

정중하게10분 늦는다는 실제 문장을 요청한 한국어 문항에서 B의 전문은 **“1~2권”**이다. 영어 답은 그런 문장을 쓰는 것이 좋은 방법이라는 자기참조 문장을 두 번 말할 뿐, 친구에게 보낼 실제 발화를 쓰지 않는다. F/Q도 지시문·`late`·`10분 늦은 시간보다` 등의 반복이어서 실제 용도와 맞지 않는 원답이다.

### 4.6 정보부족과 충분한 정보: 재출력은 확인 질문의 증거가 아님

`ko/en_info_01`은 건물 이름 없이2013년 완공됐다는 정보만 있고, `ko/en_info_03`은 지시 대상이 정해지지 않은 그 사람의 가방 색을 묻는다. 이때 기존 질문을 되풀이하거나 건물/가방을 일반적으로 설명하는 것은, 빠진 식별정보를 적절히 묻는 확인 질문과 다르다. B의 `ko_info_03` 전문 **“이마리아 가방의 가방과 무슨 색인가요?”**에는 입력에 없던 이름까지 들어간다. 질문형 끝맺음을 적절한 불확실성 처리로 자동 인정하지 않았다.

반대로 정보가 충분한 `en_role_01` 등에서 Native는 이미 주어진 수량에 답하지 않고 `What is the number?`를 다시 생성한다. 이는 과잉 재질문/질문 재출력의 표면 양상이며, 모델이 어떤 의도로 확인 질문을 했다고 단정할 근거는 없다.

충분한 정보의 `ko_info_02`에서 B의 전문 **“도서관”**은 시설 종류라는 관련 단서를 담지만 기대 명칭 `시립도서관`보다 덜 구체적이다. 영어 대응 B의 전문은 **“The city library is located in the city center of the city.”**다. 기대 시설명은 들어 있으나 이름만 지시를 지키지 않고 지문에 없던 위치를 덧붙인다. 따라서 이 둘을 의미상 전부0으로 지우거나, 반대로 단순 alias만 다른 완전 정답으로 세지 않았다.

`ko_info_04`에서 도윤의 검은 가방을 물으면 B는 **“노란 가방 색”**을 내어 다른 사람의 색을 따른다. 영어 `en_info_04`에서 B는 **“Pick a red bag and Owen's bag.”**으로 입력에 없는 red를 낸다. F는 영어 지문을 반복하면서 Owen/black 관계를 문자상 보존하나, 색 하나를 선택해 답하지는 않는다. 사실을 포함한 지문 복제와 대상 선택 성공은 다른 관측이다.

## 5. 두 언어·세 endpoint에 관해 말할 수 있는 한계

Native 두 모델은 KO에서 `각주/외부 링크/대한민국의…` 같은 분류·후미 문구나 이질 문자/접미가, EN에서 비교적 매끈한 영어 문장·질문을 길게 반복하는 표면이 보인다. 두 언어 모두 질의에 답하지 않는 반복이 존재하며 영어 문법적 유창성을 질의 해결로 환산하지 않는다. 그 후미 문구가 어느 학습자료 때문에 생겼는지나 tokenizer/훈련 원인까지 이 원형만으로 진단하지 않았다.

B는 이48개에서 짧은 stop 출력이 많고 영어 열린 설명에 일부 관련 내용이 있지만, 수량·관계·조건·형식에서 다른 실패와 잔존 반복도 보인다. F/Q가 B보다 나은 부분 답도 있으므로 단일 긍정/부정 합계로 순위를 자의 확정하지 않았다. 여러 실패 양상은 한 답에 겹친다. 예를 들어 올바른 첫문장+무관한 후미+반복+MAX_NEW를 하나의 배타적 오류 class로 강제하지 않았다.

이 자료는 고정 로컬 daily 진단이지 공식 공개 벤치마크나 blind 일반화 검증이 아니다. 학습 오염/중복과 전체 학습 조건은 이 감사 범위에서 확인하지 않았다. 모든 질문은 별도 single turn이고 history가 이어지지 않으므로 멀티턴 대화 기억·교정·질문 뒤 재답 능력은 `NOT_RUN`이다. 이 문서는 AI의 원답 정성 판독이며 독립 사람 blind 채점이나 새 gold annotation이 아니다. 기존 report의 `human_semantic_review=NOT_RUN`/pending 상태도 그대로다. 다른 태그·MTP 팔·공개MC·문법48 결과와 섞지 않았다.

## 6. 입력 보존 해시와 판독 범위

| 모델 | report 실물 SHA256 | 첫답 raw 실물 SHA256 | review 실물 SHA256 |
|---|---|---|---|
| F | `F7A795D5938D38F5B2BAE43BEFD0CE610287F22944274D31E14049DC7D3ECE92` | `791C3DE4CCF5123C9B95FAD8EBEC6F95F4CB604E913C3FA71E33C89E58D0A029` | `BBD4A210B4F53ACB61272491F972B72EA6F4DEDEAD8C6A55AA716FF5C38F238E` |
| Q | `D5BD8C8A1EFDA3EEA87D42FA9FDAD17A3506F57C59CD2BD3AB787B06A0C742D8` | `B4A8B2968B2BBC45CB1442C9D6C9D51459366E19CAE87CE90C97771D8985D000` | `F160A82A9BCB2722AA624664932F535945592F8B026BC07850C5688A08D79791` |
| B | `FE8AB080245210743DE6F28438D940E0779BA4184E22A803E44A0E24B6B9C366` | `0551CC94F55C545FFF450CD33FF7DA405303202F6C9986A522D9044977B3A440` | `C08ECBCA064B3CC9CF8D4E0C3A76D63B19F75030CBCF083FF3609F78FFF47F1E` |

실제 전문 판독 범위는 F/Q/B의 `ko_math_01`부터 `en_info_04`까지 각48개, 원형 raw1~48행 전부다. 질문48개/응답144개 중 임의 균일표본만 고른 감사가 아니다. `log-to-result`의 JSON/raw 대조·조건/관측/해석 분리 원칙을 적용했으며, 현재 승인된 출력 한 문서 밖의 결과번호·레지스트리·계획·기준표·COMPASS는 열거나 수정하지 않았다.

## 부록. 48개 ID별 실제 질문과 세 첫답

아래 질문은 전문이다. 답은 **JSON 문자열 표기**로 인용하여 실제 LF를 `\n`으로 보이게 했으며 공백·문자 정규화는 하지 않았다. 140 Unicode codepoint 이하는 전문, 초과하면 정확한 접두140자와 원답 총길이를 명시한다. 이는 display용 발췌이지 판독을140자로 제한했다는 뜻이 아니다. 생성 token 수는 raw의 generated_tokens 필드를 그대로 인용하며 글자 수로 추정하지 않았다. 원답 전문과 generated_ids·proof·시간은 §1의 raw 해당 행 및 review 동일 ID에서 확인할 수 있다. `manual`은 expected_exact=null이며 자동 의미 오답 판정이 아니다.

### 원형 01 — ko_math_01

분류: ko / arithmetic_canary / expected_exact="2"

질문 전문: `"1+1은? 답만 쓰세요."`

- F · MAX_NEW · 생성 96token · 전문 70자: `"1+1은? 답만 쓰세요.ܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ\nܡ"`
- Q · MAX_NEW · 생성 96token · 전문 128자: `"2+2은? 답만 쓰세요.so\n2+3은? 답만 쓰세요.so\n2+4은? 답만 쓰세요.so\n2+5은? 답만 쓰세요.so\n2+6은? 답만 쓰세요.so\n2+7은? 답만 쓰세요.so\n2+8은? 답만 쓰세요.so\n2+9은? 답만 쓰세요.so\n"`
- B · STOP_SEQUENCE · 생성 4token · 전문 3자: `"2+1"`

판독 메모: F/Q는 문제·변형 문제의 반복. B의2+1은 요구 숫자2 제출이 아니다.

### 원형 02 — ko_math_02

분류: ko / arithmetic_canary / expected_exact="4"

질문 전문: `"2+2는? 답만 쓰세요."`

- F · MAX_NEW · 생성 96token · 전문 70자: `"2+2는? 답만 쓰세요.ܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ\nܪ"`
- Q · MAX_NEW · 생성 96token · 전문 128자: `"2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n2+2는? 답만 쓰세요.so\n"`
- B · STOP_SEQUENCE · 생성 4token · 전문 3자: `"2+2"`

판독 메모: Native는 질문 반복, B는2+2 식을 반환한다. 계산해 대신 채점하지 않는다.

### 원형 03 — ko_math_03

분류: ko / arithmetic / expected_exact="4"

질문 전문: `"사과가 7개 있습니다. 3개를 먹으면 몇 개 남습니까? 숫자만 쓰세요."`

- F · MAX_NEW · 생성 96token · 전문 109자: `"\n사과가 7개 있습니다.\n為死\n\n사과가 7개 있습니다.\n為死\n\n사과가 7개 있습니다.\n為死\n\n사과가 7개 있습니다.\n為死\n\n사과가 7개 있습니다.\n為死\n\n사과가 7개 있습니다.\n為死\n\n사과가 7개"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/170자 발췌: `"사과가 7개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3개 있습니다. 3"`
- B · STOP_SEQUENCE · 생성 2token · 전문 1자: `"1"`

판독 메모: F는 사과7개 문장과 이질 문자를, Q는3개를 반복한다. B의1은 제시 연산 결과4와 다르다.

### 원형 04 — ko_math_04

분류: ko / arithmetic / expected_exact="24"

질문 전문: `"4 곱하기 6의 값만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/171자 발췌: `"\n4 곱하기 6의 값만 쓰세요.phal\nphal\n\n4 곱하기 6의 값만 쓰세요.phal\nphal\n\n4 곱하기 6의 값만 쓰세요.phal\nphal\n\n4 곱하기 6의 값만 쓰세요.phal\nphal\n\n4 곱하기 6의 값만 쓰세요.phal\nphal\n\n4 곱하"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/168자 발췌: `"4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세요.heim\n4 곱하기 5의 값만 쓰세"`
- B · STOP_SEQUENCE · 생성 11token · 전문 16자: `"2 곱하기 6의 값만 쓰세요."`

판독 메모: F는 문제를 반복하고 Q는6을5로 바꾼 문제를 반복한다. B도2 곱하기6이라는 변경 지시문으로 결과24를 제출하지 못한다.

### 원형 05 — en_math_01

분류: en / arithmetic_canary / expected_exact="2"

질문 전문: `"What is 1+1? Write only the number."`

- F · MAX_NEW · 생성 96token · 전문 131자: `"What is 1+1? Write only the number.enz\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1 = 1+1\n≈1"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/264자 발췌: `"What is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is "`
- B · STOP_SEQUENCE · 생성 4token · 전문 3자: `"2+1"`

판독 메모: 영어 canary도 질문 반복/문제 변경. B는 한국어와 동일한2+1을 낸다.

### 원형 06 — en_math_02

분류: en / arithmetic_canary / expected_exact="4"

질문 전문: `"What is 2+2? Write only the number."`

- F · MAX_NEW · 생성 96token · 정확 접두140/270자 발췌: `"What is 2+2? Write only the number.enz\nenz\nWhat is 2+2? Write only the number.enz\nenz\nWhat is 2+2? Write only the number.enz\nenz\nWhat is 2+2"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/264자 발췌: `"What is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is 2+2? Write the number.so\nWhat is "`
- B · STOP_SEQUENCE · 생성 4token · 전문 3자: `"2+2"`

판독 메모: B는 식2+2를 되돌리고 Native는 반복한다. 숫자4와 출력 형식은 별개다.

### 원형 07 — en_math_03

분류: en / arithmetic / expected_exact="4"

질문 전문: `"There are 7 apples. You eat 3. How many remain? Write only the number."`

- F · MAX_NEW · 생성 96token · 정확 접두140/298자 발췌: `"The apple is a fruit. It is a fruit. It is a fruit. It is a fruit.\nThe apple is a fruit. It is a fruit.\nThe apple is a fruit. It is a fruit."`
- Q · MAX_NEW · 생성 96token · 정확 접두140/459자 발췌: `"The number of apples is the number of the number of people is the number of people is the number of people is the number of people is the nu"`
- B · STOP_SEQUENCE · 생성 3token · 전문 8자: `"8 apples"`

판독 메모: F는 과일 일반론, Q는 number/people 루프, B는8 apples로 수량이 다르다.

### 원형 08 — en_math_04

분류: en / arithmetic / expected_exact="24"

질문 전문: `"Write only the value of 4 times 6."`

- F · MAX_NEW · 생성 96token · 정확 접두140/272자 발췌: `"Write only the value of 4 times 6.ܡ\nWrite only the value of 4 times 6.ܡ\nWrite only the value of 4 times 6.ܡ\nWrite only the value of 4 times "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/296자 발췌: `"Write only the value of 4 times 6.so\nWrite only the value of 4 times 6.so\nWrite only the value of 4 times 6.so\nWrite only the value of 4 tim"`
- B · STOP_SEQUENCE · 생성 2token · 전문 1자: `"5"`

판독 메모: F/Q는 지시문 반복, B는5. 요구한4×6의 결과 제출이 아니다.

### 원형 09 — ko_role_01

분류: ko / context_target / expected_exact="17"

질문 전문: `"민수는 사과 12개, 영희는 사과 17개를 가지고 있습니다. 영희의 사과는 몇 개입니까? 숫자만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/191자 발췌: `"\n민수는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/191자 발췌: `"민수는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 12개, 영희는 사과 1"`
- B · STOP_SEQUENCE · 생성 3token · 전문 2자: `"민수"`

판독 메모: F/Q는 영희17을12로 바꿔 반복하고 B는 수량 대신 민수를 낸다.

### 원형 10 — ko_role_02

분류: ko / context_target / expected_exact="12"

질문 전문: `"영희는 사과 17개, 민수는 사과 12개를 가지고 있습니다. 민수의 사과는 몇 개입니까? 숫자만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/307자 발췌: `"\n각주\n\n외부 링크 \n\n대한민국의 기업\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/183자 발췌: `"영희는 사과 17개, 민수의 사과는 한데 있어, 사과 17개, 민수의 사과는 한데 있어, 사과 17개, 민수의 사과는 한데 있어, 사과 17개, 민수의 사과는 한데 있어, 사과 17개, 민수의 사과는 한데 있어, 사과 17개, 민수의 사과는 한데 있어"`
- B · MAX_NEW · 생성 96token · 정확 접두140/191자 발췌: `"민수는 사과 17개, 민수는 사과 18개, 민수는 사과 20개, 민수는 사과 21개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 22개, 민수는 사과 2"`

판독 메모: F는 무관 분류문구, Q는17 및 문장 반복, B는 수량을 증가시키다22를 반복한다.

### 원형 11 — ko_role_03

분류: ko / context_relation / expected_exact="수진"

질문 전문: `"수진은 지도를 만들고, 태호는 지도를 읽었습니다. 지도를 만든 사람은 누구입니까? 이름만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/283자 발췌: `"\n각주 \n\n대한민국의 음악 그룹\n대한민국의 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 팝 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/172자 발췌: `"수진은 지도를 만들었습니다. 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n수진은 지도를 만들었습니다.\n"`
- B · STOP_SEQUENCE · 생성 9token · 전문 14자: `"지도는 지도를 읽었습니다."`

판독 메모: Q의 첫 수진-만들었다 문장은 관계에 맞는 일부 내용이나 이름만 지시·종료 실패가 함께 있다.

### 원형 12 — ko_role_04

분류: ko / context_relation / expected_exact="태호"

질문 전문: `"수진은 지도를 만들고, 태호는 지도를 읽었습니다. 지도를 읽은 사람은 누구입니까? 이름만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/283자 발췌: `"\n각주 \n\n대한민국의 음악 그룹\n대한민국의 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 팝 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 댄스 음악 그룹\n대한민국의 "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/179자 발췌: `"수진은 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지도를 읽었습니다. 주진이 지"`
- B · STOP_SEQUENCE · 생성 11token · 전문 20자: `"지도는 지도를 읽고 쓰는 사람입니다."`

판독 메모: Q는 읽은 대상을 수진/주진으로 바꾸고 B도 이름 대신 지도가 읽는다는 식의 답을 낸다.

### 원형 13 — en_role_01

분류: en / context_target / expected_exact="17"

질문 전문: `"Mina has 12 apples and Jina has 17 apples. How many apples does Jina have? Write only the number."`

- F · MAX_NEW · 생성 96token · 정확 접두140/355자 발췌: `"Mina has 12 apples and Jina has 16 apples. What is the number? Write only the number.\nMina has 12 apples and Jina has 16 apples. What is the"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/351자 발췌: `"Mina has 12 apples and Jina has 12 apples. How many apples do Jina have? Write the number.\nMina has 12 apples and Jina has 12 apples. How ma"`
- B · STOP_SEQUENCE · 생성 3token · 전문 9자: `"12 apples"`

판독 메모: Jina17 질문에F는16,Q는12로 문맥을 변형하고 B는12 apples를 낸다.

### 원형 14 — en_role_02

분류: en / context_target / expected_exact="12"

질문 전문: `"Jina has 17 apples and Mina has 12 apples. How many apples does Mina have? Write only the number."`

- F · MAX_NEW · 생성 96token · 정확 접두140/354자 발췌: `"Jina has 12 apples. What is the number? Write only the number.\nJina has 12 apples. What is the number? Write only the number.\nJina has 12 ap"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/434자 발췌: `"Jina is a little bit more than a little bit more than a little bit more than a little bit more than a little bit more than a little bit more"`
- B · STOP_SEQUENCE · 생성 3token · 전문 9자: `"17 apples"`

판독 메모: F는 Jina12라고 해 대상이 다르고 Q는 비교어 루프, B는17 apples로 Mina12와 다르다.

### 원형 15 — en_role_03

분류: en / context_relation / expected_exact="Nora"

질문 전문: `"Nora drew a map and Owen read it. Who drew the map? Write only the name."`

- F · MAX_NEW · 생성 96token · 정확 접두140/309자 발췌: `"Nora was a very good person. He was very good.\nNora was a very good person.\nNora was a very good person.\nNora was a very good person.\nNora w"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/308자 발췌: `"Nora's map is a map of the world. It is a map of the world. It is a map of the world. It is a map of the world. It is a map of the world. It"`
- B · STOP_SEQUENCE · 생성 38token · 정확 접두140/152자 발췌: `"Nora's map is a simple map that is easy to understand and easy to read. It is a simple and easy to read map that is easy to understand and e"`

판독 메모: Nora 출현만으로 drew 관계 해결을 인정하지 않는다. 성격/지도 설명으로 질의를 벗어난다.

### 원형 16 — en_role_04

분류: en / context_relation / expected_exact="Owen"

질문 전문: `"Nora drew a map and Owen read it. Who read the map? Write only the name."`

- F · MAX_NEW · 생성 96token · 정확 접두140/278자 발췌: `"Nora wrote the map.\nNora wrote the map.\nNora wrote the map.\nNora wrote the map.\nNora wrote the map.\nNora wrote the map.\nNora wrote the map.\n"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/292자 발췌: `"Nora's name is a name that is not a name.\nNora's name is a name that is not a name.\nNora's name is a name that is not a name.\nNora's name is"`
- B · STOP_SEQUENCE · 생성 34token · 정확 접두140/145자 발췌: `"The map is a simple and simple way to get information about the area of the sky. It is a simple way to get information about the area of the"`

판독 메모: 누가 읽었는지 대신 Nora가 썼다/이름 일반론/하늘 정보 설명을 낸다.

### 원형 17 — ko_logic_01

분류: ko / logic / expected_exact="거짓"

질문 전문: `"A는 참이고 B는 거짓입니다. A AND B는 참입니까, 거짓입니까? 참 또는 거짓 중 하나만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/175자 발췌: `"A는 거짓이고 B는 거짓입니다. A는 거짓입니다.\n\nA는 거짓입니다. A는 거짓입니다. A는 거짓입니다.\n\nA는 거짓입니다. A는 거짓입니다. A는 거짓입니다.\n\nA는 거짓입니다. A는 거짓입니다. A는 거짓입니다.\n\nA는 거짓입니다. A는 거짓입니다"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/172자 발췌: `"A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입니다. A는 참입"`
- B · STOP_SEQUENCE · 생성 2token · 전문 1자: `"A"`

판독 메모: F는 입력의A=true를false로 바꾼다. false 계열 단어 출현을 AND 정답으로 새 추출하지 않는다.

### 원형 18 — ko_logic_02

분류: ko / logic / expected_exact="참"

질문 전문: `"A는 참이고 B는 거짓입니다. A OR B는 참입니까, 거짓입니까? 참 또는 거짓 중 하나만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/238자 발췌: `"A는 거짓이고 B는 거짓입니다. A OR B는 거짓입니다.\n\n같이 보기 \n 거짓 거짓\n 거짓 거짓\n 거짓 거짓\n 거짓 거짓\n 거짓 거짓 거짓\n 거짓 거짓 거짓\n 거짓 거짓 거짓 거짓\n 거짓 거짓 거짓 거짓\n 거짓 거짓 거짓 거짓\n 거짓 거짓 거짓 거짓"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/175자 발췌: `"A는 참이고 B는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 거짓입니다.\nA는 거짓입니다. A는 "`
- B · STOP_SEQUENCE · 생성 2token · 전문 1자: `"A"`

판독 메모: 전제/연산 문장을 변형한다. B는 AND와 똑같은A를 낸다.

### 원형 19 — ko_logic_03

분류: ko / condition_update / expected_exact="11"

질문 전문: `"처음 상자에는 연필이 8개 있었습니다. 연필을 5개 더 넣고 2개 꺼냈습니다. 지금 몇 개입니까? 숫자만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/306자 발췌: `"\n각주\n\n외부 링크 \n\n대한민국의 기업\n대한민국의 기업\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/167자 발췌: `"처음 상자에는 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개 있었다.\n\n 연필이 8개"`
- B · STOP_SEQUENCE · 생성 3token · 전문 2자: `"5개"`

판독 메모: 초기8 또는더한5에 머물거나 분류문구로 이탈한다. 변경 후11을 내지 않는다.

### 원형 20 — ko_logic_04

분류: ko / condition_update / expected_exact=manual

질문 전문: `"A 상자는 빨강이고 B 상자는 파랑입니다. 이제 B 상자만 초록으로 바꿨습니다. A 상자의 색만 쓰세요."`

- F · EOS · 생성 15token · 전문 27자: `"A 상자는 빨강입니다.\n\n각주 \n\n대한민국의 음악"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/164자 발췌: `"A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강이다. A 상자는 빨강"`
- B · STOP_SEQUENCE · 생성 4token · 전문 4자: `"B 상자"`

판독 메모: F/Q는 A빨강이라는 일부를 보존하지만 후미/반복이 있다. B는 물은 색 대신B상자다.

### 원형 21 — en_logic_01

분류: en / logic / expected_exact="false"

질문 전문: `"A is true and B is false. Is A AND B true or false? Write only true or false."`

- F · MAX_NEW · 생성 96token · 정확 접두140/277자 발췌: `"A is true or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/292자 발췌: `"A is false or false.\nA is false or false.\nA is false or false.\nA is false or false.\nA is false or false.\nA is false or false.\nA is false or "`
- B · STOP_SEQUENCE · 생성 6token · 전문 19자: `"A is false or false"`

판독 메모: false가 들어가도 A의 전제나 연산을 바꾼 문장이다. 단어만 추출한 재채점은 하지 않는다.

### 원형 22 — en_logic_02

분류: en / logic / expected_exact="true"

질문 전문: `"A is true and B is false. Is A OR B true or false? Write only true or false."`

- F · MAX_NEW · 생성 96token · 정확 접두140/277자 발췌: `"A is true or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/278자 발췌: `"A is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false or B is false.\nA is false"`
- B · STOP_SEQUENCE · 생성 67token · 정확 접두140/207자 발췌: `"A is false or false. Is A OR B true or false?\nA is false or false. Is A OR B false or false?\nA is false or false. Is A OR B false or false?\n"`

판독 메모: F는 AND와 전문이 같다. Q/B도 false 문장/질문을 반복해 OR 구별을 해결하지 않는다.

### 원형 23 — en_logic_03

분류: en / condition_update / expected_exact="11"

질문 전문: `"A box had 8 pencils. You added 5 and removed 2. How many pencils are in the box now? Write only the number."`

- F · MAX_NEW · 생성 96token · 정확 접두140/332자 발췌: `"A box has 8 pencils. You added 3. How many pencils are in the box now? Write only the number.\nA box has 8 pencils. You added 3. How many pen"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/334자 발췌: `"A box has 8 pencils. You added 5 pencils. You added 5 pencils. You added 5 pencils. You added 5 pencils. You added 5 pencils. You added 5 pe"`
- B · MAX_NEW · 생성 96token · 정확 접두140/196자 발췌: `"1 pencils are 1,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,"`

판독 메모: F는 added3로 바꾸고 Q는 added5 반복, B는 큰0 수열로 반복한다.

### 원형 24 — en_logic_04

분류: en / condition_update / expected_exact=manual

질문 전문: `"Box A is red and box B is blue. Only box B is changed to green. Write only the color of box A."`

- F · MAX_NEW · 생성 96token · 정확 접두140/365자 발췌: `"Box B is red and box B is blue. Write only the color of box B. Write only the color of box B. Write only the color of box B. Write only the "`
- Q · MAX_NEW · 생성 96token · 정확 접두140/248자 발췌: `"Box A is red and box A is red.\nBox A is red and box A is red.\nBox A is red and box A is red.\nBox A is red and box A is red.\nBox A is red and"`
- B · MAX_NEW · 생성 96token · 정확 접두140/216자 발췌: `"B is red and box B is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB is blue.\nB "`

판독 메모: Q는 A red 정보를 보존하나 반복한다. F/B는B로 대상을 바꾸며 색 선택을 놓친다.

### 원형 25 — ko_format_01

분류: ko / exact_format / expected_exact="1"

질문 전문: `"다른 말 없이 1만 출력하세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/298자 발췌: `"\n각주\n\n외부 링크 \n\n대한민국의 자동차 제조 기업\n대한민국의 기업\n대한민국의 브랜드\n대한민국의 자동차 제조 기업\n대한민국의 브랜드\n대한민국의 자동차 제조 기업\n대한민국의 브랜드\n대한민국의 자동차 제조 기업\n대한민국의 브랜드\n대한민국의 자동차 제조 기"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/283자 발췌: `"2차분한 출력하세요.so\n3차분한 출력하세요.so\n\n각주 \n\n대한민국의 텔레비전 프로그램\n대한민국의 텔레비전 파일럿 프로그램\n대한민국의 파일럿 프로그램\n대한민국의 텔레비전 파일럿 프로그램\n대한민국의 리얼리티 텔레비전 프로그램\n대한민국의 리얼리티 텔레비"`
- B · STOP_SEQUENCE · 생성 7token · 전문 9자: `"1만 출력하세요."`

판독 메모: F/Q는 후미·지시문 변형, B는1만 출력하라는 명령을 돌려준다.

### 원형 26 — ko_format_02

분류: ko / exact_format / expected_exact="확인완료"

질문 전문: `"문자열 확인완료 를 그대로 한 번만 출력하세요. 설명은 붙이지 마세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/192자 발췌: `"\n같이 보기 \n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n 입력\n"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/176자 발췌: `"문자열 확인완료 를 그대로 한 번만 출력하세요. 설명은 붙이지 마세요.\n문자열 확인완료 를 그대로 한 번만 출력하세요. 설명은 붙이지 마세요.\n문자열 확인완료 를 그대로 한 번만 출력하세요. 설명은 붙이지 마세요.\n문자열 확인완료 를 그대로 한 번만 "`
- B · STOP_SEQUENCE · 생성 14token · 전문 24자: `"열 확인완료 를 그대로 한 번만 출력하세요."`

판독 메모: 확인완료 문자열 포함과 그것만 한 번 출력한 것은 다르다. Q/B는 지시문을 함께 낸다.

### 원형 27 — ko_format_03

분류: ko / exact_format / expected_exact=manual

질문 전문: `"정수 7을 answer 키의 값으로 가진 JSON 객체만 출력하세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/204자 발췌: `"정수 7을 answer 키의 값으로 가진 JSON 객체만 출력하세요.phal\nphal\n정수 7을 answer 키의 값으로 가진 JSON 객체만 출력하세요.phal\nphal\n정수 7을 answer 키의 값으로 가진 JSON 객체만 출력하세요.phal\np"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/154자 발췌: `"정수 7을 answer 키의 값으로 가진 JSON 객체만 출력하세요.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so.so."`
- B · MAX_NEW · 생성 96token · 정확 접두140/203자 발췌: `"JSON 객체 1을 answer 키의 값으로 가진 JSON 객체 2를 answer 키의 값으로 가진 JSON 객체 3을 answer 키의 값으로 가진 JSON 객체 4를 answer 키의 값으로 가진 JSON 객체 5를 answer 키의 값으로 가진 "`

판독 메모: 세 원답 모두 JSON 객체 대신 지시문/객체 문구/번호를 나열한다. 새 자동JSON 점수는 없다.

### 원형 28 — ko_format_04

분류: ko / exact_format / expected_exact="나"

질문 전문: `"가, 나, 다 중 두 번째 글자만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/195자 발췌: `"가, 나, 다 중 두 번째 글자만 쓰세요.phal\nphal, 나, 다 중 두 번째 글자만 쓰세요.phal\nphal, 나, 다 중 두 번째 글자만 쓰세요.phal\nphal, 나, 다 중 두 번째 글자만 쓰세요.phal\nphal, 나, 다 중 두 번째 글"`
- Q · MAX_NEW · 생성 96token · 전문 109자: `"가, 나, 다 중 두 번째 글자만 쓰세요.dy\n\n각주 \n\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나\n나"`
- B · STOP_SEQUENCE · 생성 14token · 전문 23자: `"가, 나, 다 중 두 번째 글자만 쓰세요."`

판독 메모: Q에나가 반복돼 맞는 글자의 일부 단서는 있지만 한 글자 출력과 종료를 지키지 못한다.

### 원형 29 — en_format_01

분류: en / exact_format / expected_exact="1"

질문 전문: `"Output only the digit 1, with no other text."`

- F · MAX_NEW · 생성 96token · 정확 접두140/299자 발췌: `"Output only the digit 1, with no other text.炯\nOutput only the digit 1, with no other text.炯\nOutput only the digit 1, with no other text.炯\nOu"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/346자 발췌: `"Input only the digit 1, with no other textual input.\nOutput only the digit 1, with no other textual input.\nOutput only the digit 1, with no "`
- B · STOP_SEQUENCE · 생성 16token · 전문 67자: `"The digit 1 is the digit number of the digit of the previous digit."`

판독 메모: 숫자1 출력 대신 지시문 또는 digit 정의식 문장을 낸다.

### 원형 30 — en_format_02

분류: en / exact_format / expected_exact="ready"

질문 전문: `"Output exactly the word ready once, without explanation."`

- F · MAX_NEW · 생성 96token · 정확 접두140/456자 발췌: `"Output exactly the word ready once, without explanation.\nOutput exactly the word ready once, without explanation.\nOutput exactly the word re"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/422자 발췌: `"In the case of the first person, the second person is the second person.\nIn the second person, the second person is the second person.\nIn th"`
- B · MAX_NEW · 생성 96token · 정확 접두140/320자 발췌: `"- ready once again.\n- ready once again.\n- ready once again.\n- ready once again.\n- ready once again.\n- ready once again.\n- ready once again.\n"`

판독 메모: F는 지시문, Q는 person 일반론, B는ready once again 목록을 반복한다.

### 원형 31 — en_format_03

분류: en / exact_format / expected_exact=manual

질문 전문: `"Output only a JSON object whose answer key has the integer value 7."`

- F · MAX_NEW · 생성 96token · 정확 접두140/322자 발췌: `"Output only a JSON object whose answer key has the integer value 7.為\nOutput only a JSON object whose answer key has the integer value 7.為\nOu"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/321자 발췌: `"Output only a JSON object whose answer key is the integer value 7.ﬁt\nOutput only a JSON object whose answer key is the integer value 7.ﬁt\nOu"`
- B · MAX_NEW · 생성 96token · 정확 접두140/341자 발췌: `"The JSON object whose answer key has the integer value 7.\n\nThe JSON object whose answer key has the integer value 7.\n\nThe JSON object whose "`

판독 메모: JSON 형태의 실제 객체 대신 해당 조건을 설명/복제한 문장이 반복된다.

### 원형 32 — en_format_04

분류: en / exact_format / expected_exact="B"

질문 전문: `"Write only the second letter in A, B, C."`

- F · MAX_NEW · 생성 96token · 정확 접두140/291자 발췌: `"Write only the third letter in A, B, C.phal\nWrite only the third letter in A, B, C.phal\nWrite only the third letter in A, B, C.phal\nWrite on"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/163자 발췌: `"Write to the second letter in A, B, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C, C,"`
- B · STOP_SEQUENCE · 생성 15token · 전문 48자: `"The first letter is the first letter of A, B, C."`

판독 메모: F는 second를third로 바꾸고 Q는C를 반복, B는first letter를 설명해 요청과 다르다.

### 원형 33 — ko_open_01

분류: ko / everyday_explanation / expected_exact=manual

질문 전문: `"사과가 어떤 과일인지 두 문장으로 알려 주세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/231자 발췌: `"\n사과가 어떤 과일인지 두 문장으로 알려 주세요.phal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\nphal\npha"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/174자 발췌: `"사과가 어떤 과일인지 두 문장으로 알려 주세요.dy\n사과가 어떤 과일인지 두 문장으로 알려 주세요.dy\n사과가 어떤 과일인지 두 문장으로 알려 주세요.dy\n사과가 어떤 과일인지 두 문장으로 알려 주세요.dy\n사과가 어떤 과일인지 두 문장으로 알려 주세"`
- B · STOP_SEQUENCE · 생성 4token · 전문 4자: `"과일인지"`

판독 메모: F/Q는 질문·접미 반복, B는과일인지 조각으로 두 문장 설명이 아니다.

### 원형 34 — ko_open_02

분류: ko / everyday_explanation / expected_exact=manual

질문 전문: `"농구가 어떤 운동인지 처음 듣는 사람에게 설명해 주세요."`

- F · MAX_NEW · 생성 96token · 전문 131자: `"\n같이 보기 \n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구\n 농구"`
- Q · EOS · 생성 18token · 전문 30자: `"농구가 어떤 운동인지 어떻게든 하는가?\n\n각주 \n\n농구"`
- B · STOP_SEQUENCE · 생성 12token · 전문 24자: `"운동인지 처음 듣는 사람에게 설명해 주세요."`

판독 메모: Q는 EOS로 끝나도 설명 대신 새 질문/각주다. B는 질문 일부만 되돌린다.

### 원형 35 — ko_open_03

분류: ko / everyday_explanation / expected_exact=manual

질문 전문: `"컴퓨터에서 파일을 폴더별로 정리하면 어떤 점이 편리한가요?"`

- F · EOS · 생성 24token · 전문 49자: `"\n같이 보기 \n 인터넷 검색\n\n각주\n\n외부 링크 \n\n인터넷 검색\n인터넷 검색\n인터넷 검색"`
- Q · EOS · 생성 36token · 전문 64자: `"컴퓨터에서 파일을 폴더별로 정리하면 어떤 점이 편리한가요?ﬁ\n\n같이 보기 \n 폴더별\n\n각주 \n\n폴더별\n컴퓨터의 목록"`
- B · STOP_SEQUENCE · 생성 12token · 전문 22자: `"폴더별로 정리하면 어떤 점이 편리한가요?"`

판독 메모: F/Q의 EOS와 B의 STOP이 폴더 정리 이점 설명 성공을 뜻하지 않는다.

### 원형 36 — ko_open_04

분류: ko / everyday_explanation / expected_exact=manual

질문 전문: `"친구에게 약속 시간보다 10분 늦는다고 정중하게 알리는 문장 하나를 써 주세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/180자 발췌: `"\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서는 다음과 같다.\n\n이 문서"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/195자 발췌: `"친구에게 약속 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 시간보다 10분 늦은 "`
- B · STOP_SEQUENCE · 생성 5token · 전문 4자: `"1~2권"`

판독 메모: F는 문서 일반론, Q는10분 문구 루프, B의1~2권은 요청 발화와 무관하다.

### 원형 37 — en_open_01

분류: en / everyday_explanation / expected_exact=manual

질문 전문: `"Describe an apple as a fruit in two sentences."`

- F · MAX_NEW · 생성 96token · 정확 접두140/322자 발췌: `"Describe a fruit in two sentences.為\nDescribe a fruit in two sentences.為\nDescribe a fruit in two sentences.為\nDescribe a fruit in two sentence"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/356자 발췌: `"Describe a fruit in two sentences.so\nDescribe a fruit in two sentences.so\nDescribe a fruit in two sentences.so\nDescribe a fruit in two sente"`
- B · STOP_SEQUENCE · 생성 34token · 정확 접두140/154자 발췌: `"The apple is a fruit that is grown in the United States and grown in the United Kingdom. It is grown in the United States and grown in the U"`

판독 메모: B는 사과/재배 문장 두 개를 내지만 반복적이고 범위가 좁다. 재배 진위의 독립 인증은 아니다.

### 원형 38 — en_open_02

분류: en / everyday_explanation / expected_exact=manual

질문 전문: `"Explain basketball to someone who has never heard of the sport."`

- F · MAX_NEW · 생성 96token · 정확 접두140/413자 발췌: `"Explain basketball to someone who has never heard of the sport.\nExplain basketball to someone who has never heard of the sport.\nExplain bask"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/421자 발췌: `"Explain basketball to someone who has never heard of the sport.so\nExplain basketball to someone who has never heard of the sport.so\nExplain "`
- B · STOP_SEQUENCE · 생성 31token · 전문 124자: `"The sport of basketball is a sport that involves the use of a ball and a basket. It involves the use of a ball and a basket."`

판독 메모: B는ball/basket라는 관련 최소 설명을 낸다. 반복·정보 부족도 있으며 의미상0으로 지우지 않는다.

### 원형 39 — en_open_03

분류: en / everyday_explanation / expected_exact=manual

질문 전문: `"Why is organizing computer files into folders useful?"`

- F · MAX_NEW · 생성 96token · 정확 접두140/352자 발췌: `"What is the difference between a file and a folder?\nA file is a file that is folded into folders.\nWhat is the difference between a folder an"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/399자 발췌: `"The first thing to do is to organize the files.\nThe second thing to do is to organize the files.\nThe second thing to do is to organize the f"`
- B · MAX_NEW · 생성 96token · 정확 접두140/413자 발췌: `"Creating folders is a complex process, but it is important to understand the basic principles of folding. Here are some basic principles tha"`

판독 메모: F는 file/folder의 잘못된 정의식 반복, Q는정리하라 반복, B는folding으로 의미를 이탈한다.

### 원형 40 — en_open_04

분류: en / everyday_explanation / expected_exact=manual

질문 전문: `"Write one polite sentence telling a friend that you will be ten minutes late."`

- F · MAX_NEW · 생성 96token · 정확 접두140/420자 발췌: `"Write one polite sentence telling a friend that you will be ten minutes late.phalting\nWrite one polite sentence telling a friend that you wi"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/476자 발췌: `"Write one polite sentence telling a friend that you will be ten minutes late late late late late late late late late late late late late lat"`
- B · STOP_SEQUENCE · 생성 59token · 정확 접두140/260자 발췌: `"The sentence telling a friend that you will be ten minutes late is a good way to tell a friend that you will be ten minutes late.\n\nThe sente"`

판독 메모: B도 지각을 알릴 실제 한 문장 대신 그 문장이 좋은 방법이라는 자기참조를 반복한다.

### 원형 41 — ko_info_01

분류: ko / missing_information / expected_exact=manual

질문 전문: `"2013년에 완공된 건물에는 무엇이 들어서 있습니까?"`

- F · MAX_NEW · 생성 96token · 정확 접두140/300자 발췌: `"\n각주\n\n외부 링크 \n\n대한민국의 리조트\n대한민국의 호텔\n대한민국의 호텔\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드\n대한민국의 브랜드"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/197자 발췌: `"2013년에 완공된 건축물에는 무엇이 들어 있습니까?sososososososososososososososososososososososososososososososososososososososososososososososososososososososos"`
- B · EOS · 생성 42token · 전문 116자: `"\n각주\n\n외부 링크 \n\n대한민국의 없어진 건축물\n대한민국의 없어진 건축물\n대한민국의 없어진 luckiest\n대한민국의 없어진 luckiest\n대한민국의 없어진 luckiest\n대한민국의 없어진 luckiest"`

판독 메모: 건물 정체가 없는 질문에서 적절한 대상 식별 질문 대신 후미/복제/이질 단어 반복을 낸다.

### 원형 42 — ko_info_02

분류: ko / sufficient_information / expected_exact="시립도서관"

질문 전문: `"지문: 별빛센터는 2013년에 완공되었고, 안에는 시립도서관이 들어섰습니다. 질문: 별빛센터 안에는 무엇이 들어섰습니까? 시설 이름만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/220자 발췌: `"\n각주\n\n외부 링크 \n\n대한민국의 도서관\n서울특별시의 도서관\n서울 강남구의 건축물\n서울 강남구의 교육\n서울 강남구의 건축물\n서울 강남구의 교육\n서울 강남구의 건축물\n서울 강남구의 교육\n서울 강남구의 건축물\n서울 강남구의 교육\n서울 강남구의 건축물\n서울"`
- Q · EOS · 생성 15token · 전문 30자: `"\n각주\n\n외부 링크 \n\n대한민국의 도서관\n도서관\n도서관"`
- B · STOP_SEQUENCE · 생성 2token · 전문 3자: `"도서관"`

판독 메모: B의도서관은 관련 시설종류 단서지만시립 명칭을 빠뜨렸다. Native의 분류문구와도 구분한다.

### 원형 43 — ko_info_03

분류: ko / missing_information / expected_exact=manual

질문 전문: `"그 사람의 가방은 무슨 색인가요?"`

- F · EOS · 생성 25token · 전문 62자: `"\n각주\n\n외부 링크 \n\n대한민국의 영화 작품\n대한민국의 영화 작품\n대한민국의 드라마 영화\n대한민국의 로맨스 영화"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/183자 발췌: `"그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가요?heim\n그 사람에게는 무슨 색인가"`
- B · STOP_SEQUENCE · 생성 15token · 전문 21자: `"이마리아 가방의 가방과 무슨 색인가요?"`

판독 메모: B는 입력에 없는 이름을 보태 질문한다. 질문형이라고 적절한 정보부족 처리로 세지 않는다.

### 원형 44 — ko_info_04

분류: ko / sufficient_information / expected_exact=manual

질문 전문: `"지문: 은지는 노란 가방을 들고 있고, 도윤은 검은 가방을 들고 있습니다. 질문: 도윤의 가방 색만 쓰세요."`

- F · MAX_NEW · 생성 96token · 정확 접두140/159자 발췌: `"지문: 은지는 노란 가방을 들고 있습니다.為紙\nphalch: 은지는 노란 가방을 들고 있습니다.為紙\nphalch: 은지는 노란 가방을 들고 있습니다.為紙\nphalch: 은지는 노란 가방을 들고 있습니다.為紙\nphalch: 은지는 노란 가방을 들고 있습"`
- Q · EOS · 생성 13token · 전문 14자: `"\n각주 \n\n가방\n가방\n가방"`
- B · STOP_SEQUENCE · 생성 6token · 전문 7자: `"노란 가방 색"`

판독 메모: 도윤의검은 가방에 대해 F는은지의노랑 문맥을 복제하고 B도노랑으로 대상을 혼동한다.

### 원형 45 — en_info_01

분류: en / missing_information / expected_exact=manual

질문 전문: `"What is inside the building completed in 2013?"`

- F · MAX_NEW · 생성 96token · 정확 접두140/435자 발췌: `"What is inside the building?phal\nphalphal is a building that is built in the same way as a building that is built in the same way as a build"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/454자 발췌: `"What is the building?so the building is a building that is a building that is a building that is a building that is a building that is a bui"`
- B · MAX_NEW · 생성 96token · 정확 접두140/481자 발췌: `"The building completed in 2013 was completed in the following year:\n\nThe building completed in 2013 was completed in the following year:\n\nTh"`

판독 메모: 건물 식별정보 부족을 해결/확인하지 않고 정의식·완공 연도 문장 반복으로 이동한다.

### 원형 46 — en_info_02

분류: en / sufficient_information / expected_exact="city library"

질문 전문: `"Passage: Star Center was completed in 2013 and houses the city library. Question: What facility does Star Center house? Write only the facility name."`

- F · MAX_NEW · 생성 96token · 정확 접두140/348자 발췌: `"Passage: Star Center is located in the city of Venice. The city is located in the city of Venice.\nPassage: Star Center is located in the cit"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/383자 발췌: `"Passage: Star Center is a private library that is located in the city of Star Center. It is located in the city of Star Center.\nPassage: Sta"`
- B · STOP_SEQUENCE · 생성 14token · 전문 59자: `"The city library is located in the city center of the city."`

판독 메모: B에city library는 있지만 지문 밖 위치를 덧붙인다. 완전 의미정답/단순alias로 확정하지 않는다.

### 원형 47 — en_info_03

분류: en / missing_information / expected_exact=manual

질문 전문: `"What color is that person's bag?"`

- F · MAX_NEW · 생성 96token · 정확 접두140/350자 발췌: `"What is the bag?phal\nphalphalphalphalphalphal\nphalphalphalphalphalphalphalphal\nphalphalphalphalphalphalphalphalphal\nphalphalphalphalphalphal"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/342자 발췌: `"What color is that person's bag?so\nWhat color is that person's bag?so\nWhat color is that person's bag?so\nWhat color is that person's bag?so\n"`
- B · STOP_SEQUENCE · 생성 37token · 정확 접두140/153자 발췌: `"The bag is a small piece of cloth that is covered with a thin layer of fabric. It is made of a variety of materials, including cotton, cotto"`

판독 메모: B의 가방 재질 설명은 색/대상 확인이 아니다. F/Q의 질문 복제와 구분되는 무관 설명이다.

### 원형 48 — en_info_04

분류: en / sufficient_information / expected_exact="black"

질문 전문: `"Passage: Mina carries a yellow bag and Owen carries a black bag. Question: Write only the color of Owen's bag."`

- F · MAX_NEW · 생성 96token · 정확 접두140/326자 발췌: `"Passage: Mina carries a yellow bag and Owen carries a black bag.\nPassage: Mina carries a yellow bag and Owen carries a black bag.\nPassage: M"`
- Q · MAX_NEW · 생성 96token · 정확 접두140/306자 발췌: `"Passage: Mina carries a yellow bag and Owen's bag. Verify the color of Owen's bag. Verify the color of Owen's bag. Verify the color of Owen'"`
- B · STOP_SEQUENCE · 생성 12token · 전문 30자: `"Pick a red bag and Owen's bag."`

판독 메모: F는black 관계를 포함한 지문을 복제할 뿐 선택 답은 아니다. Q는verify질문 반복, B는근거없는red다.
