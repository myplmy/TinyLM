# 검산 가능한 direct 첫답 감사 — 조회·갱신의 제한적 개선과 산수·표현 의존 실패

같은 부모의 고정 TEST에서 코드 검산 정답은 0/1,024에서 direct 424/1,024로 늘었다. direct는 1,024답 모두 지정 형식으로 종료했지만, 값 오답은 600개다. 가족별로 addition 38/512, lookup 202/256, update 184/256이며 산수와 조회·갱신을 하나의 일반 추론 점수로 묶으면 안 된다.

조회·갱신에는 단순 첫 값·이전 값·마지막 갱신값 고정 복사만으로 설명되지 않는 신규 조건 대응이 있었다. 다만 질문을 먼저 제시한 ROOT에서 성능이 높았고, 기록을 먼저 제시한 ROOT에서는 여덟 표현을 모두 맞힌 ROOT가 하나도 없었다. 이는 범위가 좁고 표현 의존성이 남은 실제 개선이지 일반 추론·언어 품질·모델 채택의 입증이 아니다.

## 1. 범위와 증거 고정

완료된 direct `parent_ntp/report.json`, 같은 교과의 `first_answer_parent_ntp`, `first_answer_parent_baseline` 및 명시적으로 허용된 HF direct corpus의 report·고정 샤드만 읽었다. 진행 중인 trace 팔과 그 출력 디렉터리는 열거나 열거하지 않았다. 학습·모델·GPU·체크포인트 실행이나 텐서 읽기, 다운로드, 원자료·코드·기존 문서·Git 변경, 하위 에이전트 호출은 없었다. 기록 파일은 이 문서 하나다. 정식 결과·계획·원장 반영은 총괄 소유다.

| 입력 | SHA-256 |
|---|---|
| [direct 학습 report](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/parent_ntp/report.json) | `F6845DE0DC50C6DAF07BC2B3FDAE6D08EBC29709C6CAFE0E53176C68C76AC209` |
| [direct 첫답 report](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/first_answer_parent_ntp/report.json) | `4050E99C8CC93118354A96FE85CD750019DD09378F1B1D671279429DF989FCAD` |
| [원래 부모 첫답 report](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/first_answer_parent_baseline/report.json) | `5DB62CA2ECA4C03378FE467FCE20CFBA63B1C49B5BB58CF9FA7BC56C8EC6A8D8` |
| [HF direct corpus report](/home/uranus/tinyLM/HF/sft_ready/p101a_sft_mtp_verified_direct_v3_s1337/corpus/report.json) | `B814B42FC4D5B1D1AE4F1E77F03E97E73440D8EEEED031FCEEA9112F3D515AA4` |
| direct 첫답 raw concat | `7BDE4CFF57F5B244EA04D25CB8689F63084FB18F9F0241BF508E8C17DF79894E` |
| 원래 부모 첫답 raw concat | `CBA4C0571C317C77BEEE447290F8ED7E13CF621A2370F0FB05DB82177DA65D36` |

두 첫답 report는 모두 `FIRST_ANSWER_COLLECTION_COMPLETE`, 종료 코드 0이다. 실제 manifest의 바이트·행·샤드 SHA·concat SHA를 검산했고 index 0…1023을 확인했다. 두 경로의 각 `source`가 HF TEST의 같은 행과 완전히 같았다. corpus·tokenizer·평가 코드 SHA와 FP32 MATH/TF32 OFF, cache ON, MTP 추론 OFF, greedy/top1, max_new 128, retries 0, 학습 업데이트 0인 평가 계약도 같다. 부모 체크포인트는 report의 SHA 계보만 확인했으며 파일 자체는 열지 않았다.

## 2. 4,096 TRAIN ROOT와 128 TEST ROOT는 다른 분모다

실제 corpus는 `production_geometry=true`다. `meta.root`와 [canonical ROOT 정의](/home/uranus/tinyLM/scripts/p106b_verified_trace_data.py:75)를 다시 계산해 대조했다. addition은 피연산자 순서를 정규화하고, lookup/update는 이름을 정규화한 사실 표와 갱신 내용을 ROOT로 삼는다. 조회 대상이 바뀌어도 같은 사실 표이면 같은 ROOT다.

| 분할 | 실제 행 | 고유 ROOT | ROOT당 행 | addition / lookup / update ROOT | 한국어 / 영어 행 |
|---|---:|---:|---:|---|---|
| TRAIN | 4,096 | 4,096 | 1 | 2,048 / 1,024 / 1,024 | 2,048 / 2,048 |
| DEV, manifest의 val | 1,024 | 128 | 8 | 64 / 32 / 32 | 512 / 512 |
| TEST | 1,024 | 128 | 8 | 64 / 32 / 32 | 512 / 512 |

TRAIN은 ROOT당 한 언어·한 표현을 고정한 한 행이므로 **4,096행·4,096개 ROOT가 실제로 맞다**. 네 번의 학습 노출을 16,384개의 새 ROOT로 세면 안 된다. 반면 DEV/TEST는 각 ROOT를 2언어×4표현으로 펼친 1,024행이다. TEST 1,024개를 독립적인 1,024개 ROOT나 새 지식 근거로 셀 수 없다. `unique_knowledge_claim=false`인 작은 코드 생성 교과다.

세 분할 사이 ROOT 교집합과 질문 문자열의 정확 교집합은 각각 0이었다. 실제 ROOT 집합은 생산 report의 목록과도 일치했다. ROOT 분리 검사는 이름 변경·사실 순서·질문 대상 변형에 의한 같은 ROOT의 누출을 막지만, 일반적인 세계 지식 독립성이나 사전학습 중복 부재를 입증하지 않는다. TEST 정답 숫자들은 가족별 TRAIN 정답 값 집합 안에 모두 있었으며, 새 정답 어휘를 배우는 시험이 아니라 새 사실 조합·질문 조건에 맞춰 알려진 정수 값을 출력하는 시험이다.

| 고정 corpus raw | concat SHA-256 |
|---|---|
| train_000000.jsonl | `9D438D65C5B10E1D25C2FC298BB103288B4DAD25E68B7DC33C8B330695146F04` |
| val_000000.jsonl | `A29587C036B3FAD099F96A76463D75EEE9E6DA8E5C5655A47AE177012554BF44` |
| test_000000.jsonl | `EC851817F1D96B334C135C07FCD77466CFF93EC291560FFA26E1A0498F72ECF8` |

6,144개의 corpus 행에서 원문 질문의 두 피연산자 또는 기록·조회 대상·갱신을 별도 정규식으로 읽어 `meta.task`와 대조했다. ROOT·split·예약 제외·gold 값·gold의 채점도 재검산했다. 기존 생성기를 다시 돌려 같은 결과가 나왔다는 검사만으로 대신하지 않았다. 입력은 두 발화 중 user 한 개이며 gold assistant는 평가 프롬프트에서 제외된다. 풀이가 들어간 프롬프트도 아니다. 원천은 `CODE_OWNED_PROCEDURAL`이며 자연 PUBLIC 자료의 오류를 이 교과의 정답 라벨 오류로 섞지 않는다.

통계적 해석은 최소한 ROOT 단위의 묶음을 고려해야 한다. 아래 행별 정답률은 고정 시험의 기술값이고, 1,024개의 독립 시행으로 가정한 신뢰구간·유의성은 계산하지 않았다. 이후 두 팔을 비교하더라도 같은 128개 ROOT의 대응 구조를 보존해야 한다. ROOT 자체도 단일 생성 규칙·단일 seed에서 나온 것이므로 독립적인 세계 지식 표본이라는 보증은 없다.

## 3. 학습 관측과 첫답 지표의 차이

direct는 같은 P090B 부모에서 보조 head 없이 마지막 정답만 감독한 NTP 팔이다. report의 `head_tensor_bytes=0`, 보조 gradient update 0이다. 4 epoch·128 updates를 완료했고, micro 8×accum 16, seq 1024, seed 1337, checkpoint ON, compile default, Adam 5e-5/Muon 2e-4를 기록한다. 실제 누적 x는 798,252개, assistant targets는 79,520개다. 학습 report의 초기 본체 SHA는 `E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193`다.

DEV h1 CE는 7.933323→0.486039, 마지막 TRAIN h1 CE는 0.393933이다. 그러나 자유 생성 산수 정답은 38/512였다. gold 토큰 이력이 주어진 다음 토큰 손실과 자유 생성 최종값 정확도는 다른 지표다. 고정 native 첫 32 crop의 CE는 3.504322→3.641723으로 나빠졌고 전체 언어 품질의 평가가 아니다. 전 스텝 `grad_max=15.977489`이므로 낮은 마지막 CE만으로 안정성 PASS라고 부르지 않는다. 이 report만으로 warmup 이후의 최대값을 분리할 수 없다.

학습 report는 여전히 `formal_train_ready=false`와 실험용 상태를 기록한다. 실제 첫답 완료는 별도의 닫힌 report에서 확인했고, 기존 학습 report의 상태를 수정하지 않았다. 고정 8문항의 첫 시도 점수는 학습 report상 학습 전후 모두 0/8이다. 이는 별도 canary 요약이며 이번 24문항 직접 판독과 합치거나 개별 실패 내용을 추가 판정하지 않았다.

## 4. 첫답 2,048건 전량 재채점

[정본 score_response](/home/uranus/tinyLM/scripts/p106b_verified_trace_data.py:221)와 기존 첫답 `score`로 2,048답 전부를 다시 채점했고 저장된 grading 전체와 일치했다. 현재 채점 소스 SHA는 실행 report와 같은 `1B1464F606529679720778F7D74DD93A2EF358BB7A09338895D58A8FDABDB9FE`다.

이 채점은 임의의 숫자 부분 문자열을 정답으로 뽑지 않는다. 지정 언어의 마지막 줄 `답: 정수`/`Answer: integer` 계약과 코드로 계산한 실제 값을 확인한다. `final_correct`와 풀이·출력 정책 준수는 별개 필드다. 이번 direct는 전량 정책도 준수했으므로 invalid trace를 앞에 붙인 답을 정답으로 세어 424가 된 사례는 없다. 자연 QA의 annotation EM이나 세계 사실성 판정과도 다른 지표다.

| 전량 관측 | 원래 부모 | direct |
|---|---:|---:|
| 코드 검산 최종값 정답 | 0/1,024 | 424/1,024 (41.40625%) |
| addition | 0/512 | 38/512 (7.421875%) |
| lookup | 0/256 | 202/256 (78.90625%) |
| update | 0/256 | 184/256 (71.875%) |
| 한국어 / 영어 전체 | 0/512 / 0/512 | 212/512 / 212/512 |
| 최종행 형식 / direct 정책 준수 | 0 / 0 | 1,024 / 1,024 |
| 종료 합계 | 202 | 1,024 |
| EOS / STOP_SEQUENCE / MAX_NEW | 202 / 0 / 822 | 0 / 1,024 / 0 |
| 빈 답 / extraction 실패 | 0 / 0 | 0 / 0 |
| 풀이 포함 | 0 | 0 |
| 생성 토큰 합 | 110,061 | 5,012 |

기준선의 EOS 202건은 모두 한국어 addition이었다. 종료는 정답이 아니며 direct도 종료한 값 오답이 600개다. 원래 부모는 지정 최종행 형식 자체를 지킨 답이 0개였으므로, 0→424에는 형식 습득과 값 대응의 변화가 함께 들어 있다. 이를 순수한 산술·추론 능력 향상분으로 분해할 수 없다. 출력량이 다른 두 수집의 경과 시간 차이도 모델 자체의 토큰당 추론 가속으로 읽지 않는다.

### 4.1 ROOT의 모든 표현을 맞혔는가

| 가족 | 고유 TEST ROOT | 각 ROOT의 8답 모두 정답: 부모 / direct |
|---|---:|---:|
| addition | 64 | 0 / 0 |
| lookup | 32 | 0 / 14 |
| update | 32 | 0 / 13 |

addition은 20개 ROOT에서 일부 표현을 맞혔지만 8개 표현을 모두 맞힌 ROOT는 없었다. lookup/update의 완전 정답 ROOT는 뒤의 질문 먼저 배치에서만 나왔다. ROOT별 완전 정답과 전체 행별 정답률은 서로 다른 기술값이며 어느 한쪽으로 다른 쪽을 대체하지 않는다.

## 5. 지름길·표현·언어·조건 변화 진단

아래는 이번 감사의 후행 기술 진단이다. 공식 채점을 바꾸거나 새 성공 기준으로 소급 사용하지 않았다.

### 5.1 단순 고정 복사만으로는 전체 결과가 설명되지 않는다

[코드 소유 shortcut_baselines](/home/uranus/tinyLM/scripts/p106b_verified_trace_data.py)도 실제 TEST 행에서 다시 계산했다.

| TEST 가족 / 단순 규칙 | 규칙 정답 | 그 규칙이 틀리는 행에서 direct가 실제 맞힌 수 |
|---|---:|---:|
| addition: 첫 피연산자 출력 | 8/512 | 36/504 |
| addition: 큰 피연산자 출력 | 16/512 | 28/496 |
| lookup: 첫 기록 값 출력 | 128/256 | 101/128 |
| lookup: 큰 값 출력 | 128/256 | 99/128 |
| update: 첫 초기 기록 값 출력 | 64/256 | 135/192 |
| update: 첫 기록의 현재 값 출력 | 128/256 | 90/128 |
| update: 큰 현재 값 출력 | 128/256 | 89/128 |
| update: 조회 대상의 갱신 전 값 출력 | 128/256 | 90/128 |
| update: 마지막 갱신값 출력 | 128/256 | 94/128 |

lookup은 조회 대상이 첫 기록인 경우와 아닌 경우 모두 101/128을 맞혔다. update는 조회 대상이 실제로 갱신된 경우 90/128, 갱신되지 않은 경우 94/128을 맞혔다. 따라서 항상 첫 숫자·항상 큰 수·항상 이전 값·항상 마지막 갱신값 중 어느 하나만 적용한 것으로 전체 정답을 설명할 수는 없다. 이 검사로 복잡한 혼합 지름길이나 모든 편향이 배제되는 것은 아니다.

같은 ROOT·언어·기록 순서에서 질문 대상을 A↔B로 바꾸면 실제 gold도 달라진다. 두 질문을 모두 맞힌 쌍은 lookup 74/128쌍, update 67/128쌍이었다. 질문이 달라도 같은 숫자를 답한 쌍은 각각 46쌍/47쌍이었다. 이 128쌍은 가족별 32개 ROOT×2언어×2기록 순서에서 나온 묶음이며 독립적인 128개 ROOT가 아니다. 제대로 조건에 반응한 사례와 조회 대상을 무시한 듯한 실패가 함께 남아 있다.

기록 순서만 바꾸고 질문 대상·gold는 유지한 쌍에서도 lookup 14/128쌍, update 22/128쌍은 모델의 숫자 답이 바뀌었다. 기록 순서를 포함한 표현 변화에 완전히 불변인 해법은 아니다.

### 5.2 질문과 기록의 배치에 큰 조건부 차이가 있다

| 가족 | 질문 먼저: 정답 / 행, ROOT 수 | 기록 먼저: 정답 / 행, ROOT 수 | 8표현 모두 정답 ROOT: 질문 먼저 / 기록 먼저 |
|---|---|---|---|
| lookup | 123/128, 16개 ROOT | 79/128, 16개 ROOT | 14/16 / 0/16 |
| update | 118/120, 15개 ROOT | 66/136, 17개 ROOT | 13/15 / 0/17 |

생성기의 `wording=1`은 질문→기록→갱신, `wording=0`은 기록→갱신→질문이다. 이 값은 ROOT에서 결정되어 같은 ROOT의 8표현 내에서는 바뀌지 않는다. 따라서 위 차이는 다른 ROOT 구성과 교락된 조건부 관측이다. 같은 사실의 문장 순서만 바꾸어 새 모델 생성을 한 인과 실험이 아니므로 순서의 인과 효과로 단정하지 않는다. 그럼에도 현재 시험에서 성능이 어느 배치에 집중됐는지와 완전 정답이 없는 배치를 숨기면 안 된다.

lookup의 A 질문은 85/128, B 질문은 117/128이었다. 특히 기록 먼저 배치에서는 A 26/64 대 B 53/64다. 원래 두 주체의 값 크기·질문 대상·기록 첫 위치는 교차되므로 단순히 B가 항상 큰 수여서 생긴 결과라고 볼 수 없다. 원인 자체를 확정한 것은 아니며 이름·배치·수치 조합 편향을 남은 한계로 기록한다.

### 5.3 언어별 합계가 같아도 답 대응은 완전히 같지 않다

| 가족 | 한국어 | 영어 | 같은 ROOT·view에서 양쪽 모두 정답 / 언어 대응 쌍 |
|---|---:|---:|---:|
| addition | 17/256 | 21/256 | 7/256 |
| lookup | 102/128 | 100/128 | 95/128 |
| update | 93/128 | 91/128 | 82/128 |

두 언어 전체 합계는 각각 212/512지만 같은 질문 조건에서 항상 같은 값을 낸 것은 아니다. 고정 표본의 update index 859/863도 한국어는 다른 주체의 갱신값, 영어는 올바른 비갱신 주체 값을 답했다. 한영 행 수가 같다는 사실을 한영 품질의 완전한 대응이나 target 토큰 균형으로 바꾸지 않는다.

### 5.4 산수와 조회·갱신의 남은 오류

addition TEST에는 두 피연산자가 모두 한 자리인 경우가 없다. 적어도 하나가 두 자리이며, 0이 포함된 2개 ROOT의 16답은 10개 정답, 0이 없는 62개 ROOT의 496답은 28개 정답이다. 일의 자리 올림이 필요한 경우 6/200, 필요 없는 경우 32/312이며 합이 100 이상이면 9/240이다. 474개 오답 중 30개는 피연산자 중 하나를 그대로 출력했고, 444개는 다른 잘못된 숫자였다. 453개는 일의 자리 숫자부터 gold와 달랐다. 단순한 백의 자리 표기 문제만으로 설명되지 않으며 기본 산수 전반이나 예약된 1+1 질문으로의 전이를 입증하지 않는다.

lookup의 54개 오답은 다른 주체의 기록 값 46개, 두 기록 값에 없는 숫자 8개였다. update의 72개 오답은 조회 대상이 갱신됐는데 이전 값을 출력한 11개, 다른 주체의 현재 값 18개, 조회 대상은 그대로인데 다른 주체의 마지막 갱신값을 출력한 22개, 다른 주체의 초기 값 8개, 입력 숫자들에 없는 값 13개였다. 이 구분은 실제 정수·두 주체·하나의 갱신이라는 닫힌 입력에서의 기술 분류이며 내부 사고 과정의 관측이 아니다.

## 6. 가족×언어별 고정 4개: 질문·gold·부모/학생 답 직접 판독

답을 읽기 전에 각 가족×언어를 원 TEST 순서로 모아, 네 구간에서 `q*N//4+q`번째 행을 택했다(`q=0,1,2,3`). 단순히 `0,N/4,N/2,3N/4`를 택하면 현재 블록 배열에서는 모두 view 0이 되므로, 구간마다 view 0/1/2/3을 하나씩 포함하도록 고정했다. 한국어와 영어는 같은 네 ROOT·view에 대응한다. 결과로 표본을 교체하지 않았다.

24질문의 실제 원문·gold·두 경로의 답 전체·종료를 모두 읽었다. 원시 답은 [원래 부모](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/first_answer_parent_baseline/first_answers_000000.jsonl)와 [direct](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/first_answer_parent_ntp/first_answers_000000.jsonl)의 `index+1`번째 줄이다. 아래 부모 답은 긴 반복을 줄인 발췌/요약이다. 질문은 줄 경계를 `/`로 표시하고 공통 마지막 지시문만 생략했다. 공통 지시문은 한국어 `마지막 줄은 '답: 정수' 형식으로 정확히 한 번 쓰세요.`, 영어 `Write exactly one final line in the form 'Answer: integer'.`다.

`STOP`은 지정 STOP_SEQUENCE, `MAX`는 128토큰 상한이다. 학생 답은 모두 STOP으로 끝났다. 이 표본의 성공 비율을 전량 성능으로 확대하지 않는다. 예를 들어 산수 표본 8답 중 4개가 맞았지만 전량은 38/512다.

| TEST index / 언어 / view | 실제 질문 핵심과 사실, 제시 순서 유지 | gold | 부모 답·종료 | direct 첫답 / 판독 |
|---|---|---|---|---|
| 0 / ko / 0 | `64+87를 계산하세요.` | 답: 151 | `같이 보기`, `이십일` 등 / EOS | `답: 142` / 산수 오답 |
| 305 / ko / 1 | `52+36를 계산하세요.` | 답: 88 | `이십일` 반복 / EOS | `답: 88` / 정답 |
| 530 / ko / 2 | `질문: 두 수의 합은 얼마입니까? / 수: 10, 60` | 답: 70 | `이십일` 반복 / EOS | `답: 70` / 정답 |
| 787 / ko / 3 | `질문: 두 수의 합은 얼마입니까? / 수: 99, 15` | 답: 114 | `이십일` 반복 / EOS | `답: 111` / 산수 오답 |
| 4 / en / 0 | `Calculate 64+87.` | Answer: 151 | `Write a list... The following...` 반복 / MAX | `Answer: 155` / 산수 오답 |
| 309 / en / 1 | `Calculate 52+36.` | Answer: 88 | 목록과 `1.1.1...` 반복 / MAX | `Answer: 88` / 정답 |
| 534 / en / 2 | `Question: what is the sum? / Numbers: 10, 60` | Answer: 70 | 두 수의 difference를 묻는 새 질문 반복 / MAX | `Answer: 70` / 정답 |
| 791 / en / 3 | `Question: what is the sum? / Numbers: 99, 15` | Answer: 114 | `Question: 'Analytical'` 반복 / MAX | `Answer: 111` / 산수 오답 |
| 8 / ko / 0 | `질문: A의 현재 값은? / 기록: A=22; B=128` | 답: 22 | `이블의 노래` 등 무관 반복 / MAX | `답: 22` / 조회 정답 |
| 249 / ko / 1 | `질문: B의 현재 값은? / 기록: A=115; B=240` | 답: 240 | `이블의 노래` 반복 / MAX | `답: 240` / 첫 기록이 아닌 대상 조회 정답 |
| 514 / ko / 2 | `기록: B=152; A=55 / 질문: A의 현재 값은?` | 답: 55 | 가수·작사가 분류 반복 / MAX | `답: 152` / 다른 주체이자 첫 기록 값 |
| 715 / ko / 3 | `질문: B의 현재 값은? / 기록: B=111; A=14` | 답: 111 | `B` 반복 / MAX | `답: 111` / 조회 정답 |
| 12 / en / 0 | `Question: what is the current value of A? / Records: A=22; B=128` | Answer: 22 | `Answer: A=128; B=128...` 반복 / MAX | `Answer: 22` / 조회 정답 |
| 253 / en / 1 | `Question: what is the current value of B? / Records: A=115; B=240` | Answer: 240 | `A=121; B=121...` 반복 / MAX | `Answer: 240` / 첫 기록이 아닌 대상 조회 정답 |
| 518 / en / 2 | `Records: B=152; A=55 / Question: what is the current value of A?` | Answer: 55 | 같은 질문 반복 / MAX | `Answer: 152` / 다른 주체이자 첫 기록 값 |
| 719 / en / 3 | `Question: what is the current value of B? / Records: B=111; A=14` | Answer: 111 | `B=14` 반복 / MAX | `Answer: 111` / 조회 정답 |
| 16 / ko / 0 | `기록: A=220; B=238 / 변경: A=98 / 질문: A의 현재 값은?` | 답: 98 | `A=220` 반복 / MAX | `답: 238` / 다른 주체 값 |
| 161 / ko / 1 | `기록: A=251; B=126 / 변경: A=190 / 질문: B의 현재 값은?` | 답: 126 | `A=251` 반복 / MAX | `답: 190` / 물어보지 않은 주체의 갱신값 |
| 482 / ko / 2 | `질문: A의 현재 값은? / 기록: B=190; A=85 / 변경: A=74` | 답: 74 | `이블의 노래` 반복 / MAX | `답: 74` / 실제 갱신 반영 정답 |
| 859 / ko / 3 | `기록: B=198; A=97 / 변경: A=162 / 질문: B의 현재 값은?` | 답: 198 | `B=172` 반복 / MAX | `답: 162` / 갱신되지 않은 B 대신 A의 새 값 |
| 20 / en / 0 | `Records: A=220; B=238 / Update: A=98 / Question: what is the current value of A?` | Answer: 98 | 값을 되묻는 문구 반복 / MAX | `Answer: 220` / 갱신 전 stale 값 |
| 165 / en / 1 | `Records: A=251; B=126 / Update: A=190 / Question: what is the current value of B?` | Answer: 126 | current value 질문 반복 / MAX | `Answer: 127` / 입력에 없는 값 |
| 486 / en / 2 | `Question: what is the current value of A? / Records: B=190; A=85 / Update: A=74` | Answer: 74 | `B=190; A=8...` 반복 / MAX | `Answer: 74` / 실제 갱신 반영 정답 |
| 863 / en / 3 | `Records: B=198; A=97 / Update: A=162 / Question: what is the current value of B?` | Answer: 198 | current value 질문 반복 / MAX | `Answer: 198` / 다른 주체가 바뀌어도 B 값 유지 정답 |

첫 기록이 아닌 B=240을 조회하거나, A=85를 새 값 74로 바꾸어 답하거나, A만 바뀌었을 때 B=198을 유지하는 실제 정답은 형식 습득만의 예시가 아니다. 반대로 다른 주체의 값, 갱신 전 값, 입력에 없는 127, 산수 142/155/111은 형식이 맞더라도 값 오답이다. 원래 부모의 새 질문·문서 이어 쓰기·반복과도 별개의 실패 양상이다.

## 7. 허용되는 결론과 아직 말할 수 없는 것

같은 TEST·같은 부모의 단일 seed에서 지정 형식과 짧은 종료가 크게 개선됐고, 제한된 정수 조회·한 번의 갱신에서 새 ROOT의 일부 조건에 맞는 첫답이 실제로 나왔다. 단순한 첫 값·최댓값·stale 값·마지막 갱신값 하나의 고정 규칙은 전량 결과를 설명하지 못한다. 이 범위의 개선은 보존해야 한다.

동시에 산수 정확도는 낮고, 올림·표현·이름·문장 배치·언어 대응에 실패가 남았다. 원래 부모의 0점에는 형식 실패가 포함되고, direct 1,024행은 독립적인 1,024개 ROOT가 아니다. 질문 먼저와 기록 먼저의 큰 차이도 ROOT 구성과 교락된 관측이다. 숫자 두 개의 합, 두 주체의 값 조회와 한 번의 갱신을 넘어 다단계 추론·외부 사실성·일반 지능·자연 대화 품질·모델 채택을 입증한 결과가 아니다.

trace 팔의 실행 상태나 우열은 미판정이다. 이번 감사에서는 해당 경로를 열거나 열거하지 않았고, direct 결과만으로 풀이 감독의 효과 또는 손해를 주장하지 않는다. 이후 완료 통지가 와도 같은 ROOT·질문·초기화와 실제 감독 토큰·계산 비용의 차이를 구분해야 하며, 현재 고정 raw나 지표를 바꾸어 비교하지 않는다.

## 8. trace 완료 뒤 추가 감사 — 코드 교과의 큰 개선과 교과 밖 전이 실패

§1~7은 direct만 회수했던 시점의 기록으로 보존한다. 총괄이 2026-10-22 09:57:50 KST에 trace TEST 완료와 읽기 허용을 통지한 뒤 이 절을 추가했다. 추가 전 문서 SHA는 `DA276CACBE24EBCB67CFC4A10A21DFAA353CBC46D522232A7CEA8FF48B486FC3`다. 앞의 trace 미회수 상태는 당시 기록이고, 현재 완료 판정은 이 절이 소유한다. 다른 문서·코드·원자료 변경, 모델·GPU·체크포인트 실행과 학습 피드백은 없었다.

### 8.1 새 입력과 동일 조건의 실제 대응 검산

| 추가 완료 입력 | SHA-256 |
|---|---|
| [trace 학습 report](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_trace_v3_s1337/parent_ntp/report.json) | `152AFAE3545D405DBD4E05034B241B6CDE72B45236C5BEF144C2E9E58A6E2811` |
| [trace 첫답 report](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_trace_v3_s1337/first_answer_parent_ntp/report.json) | `39A27A712ECAA2E8D622019A466564923C504A91E839E9FF3515E52C9D3DB869` |
| trace TEST 첫답 raw concat | `5E68158B2F0D71B5954086122835DE36F8C797FA7A9DCBBA74537A018650AFD0` |
| [HF trace corpus report](/home/uranus/tinyLM/HF/sft_ready/p101a_sft_mtp_verified_trace_v3_s1337/corpus/report.json) | `3D4374CFB5944A703C6509F44E01D4FFA239C6D3123F1C8D54FA18622EF8CB6E` |
| trace TRAIN raw concat | `5A83019B006CEB65600498E01AE9AAD6F8DE4EE525D3A72D0664EE69D752C744` |
| trace DEV raw concat | `FC61A209402AB7AC821B8CF3C7A85DDC170D67A2D7AAE5CCE3A27C60D2FA14FA` |
| trace TEST corpus raw concat | `436E0B84F77D234235A7FA6DE4B55C2DC570875A5EDFE4A21B8E5A34769AA886` |

trace 첫답 report는 `FIRST_ANSWER_COLLECTION_COMPLETE`, 종료 코드 0이다. 새 자료의 실제 바이트·행·샤드 SHA·concat SHA를 검산했다. direct와 trace의 TRAIN 4,096행, DEV 1,024행, TEST 1,024행을 같은 순서로 대조해 user 메시지·task·ROOT·language·view·presentation·gold 값이 같음을 확인했다. metadata의 차이는 policy와 이를 포함하는 row_id이고, assistant 감독 대상은 직접 답과 단계열로 다르다. trace의 gold 단계열도 6,144행 모두 원 task에 대한 단계·최종값·일치·정책 검증을 통과했다. 평가 입력에는 user만 들어가므로 gold 단계열은 프롬프트에 없다.

원래 부모의 TEST 답은 direct 쪽의 닫힌 기준선을 재사용했다. 세 경로의 3,072답을 정본 함수로 다시 채점해 저장 grading 전체와 일치했다. 부모와 direct의 source는 완전히 같고 trace도 같은 질문·task·ROOT다. 두 학생의 초기 본체 SHA, 부모 SHA, seed·optimizer·micro/accum·seq·checkpoint·compile·4 epoch·128 updates·코드 SHA map과 평가 조건도 같다. 둘 다 보조 head 없는 NTP이며 MTP head 효과의 비교가 아니다.

| 실제 감독·입력량 | direct | trace | 해석 범위 |
|---|---:|---:|---|
| TRAIN ROOT / pass당 행 | 4,096 / 4,096 | 동일 | 같은 질문·ROOT의 네 번 노출 |
| 누적 assistant targets | 79,520 | 512,464 | trace는 6.444467배 |
| 누적 실제 x | 798,252 | 1,231,196 | trace는 1.542365배 |
| 학습 report whole_wall_sec | 411.06 | 419.12 | report의 전체 구간, 정상상태 단위 계산비 아님 |
| TEST 생성 토큰 | 5,012 | 32,090 | 출력 길이도 다름 |

ROOT와 업데이트 수는 같지만 감독 토큰·실제 입력량은 같지 않다. 검증된 짧은 단계열을 포함한 감독 패키지의 비교이지, 동일 target-token 예산의 효율 비교가 아니다. targets 6.44배를 계산비나 wall time 6.44배로 바꿔 읽을 수도 없다. 단계 구조와 추가 감독량의 효과를 분리하지 않았으며, 직접 답과 단계열의 CE는 대상 자체가 달라 수치만으로 추론력을 비교하지 않는다.

### 8.2 최종값·단계 검증·정책 준수는 별도 지표다

| 같은 고정 TEST의 최종값 정답 | 원래 부모 | direct | trace |
|---|---:|---:|---:|
| 전체 | 0/1,024 | 424/1,024 | 1,003/1,024 (97.949219%) |
| addition 한국어 / 영어 | 0 / 0 | 17/256 / 21/256 | 255/256 / 242/256 |
| lookup 한국어 / 영어 | 0 / 0 | 102/128 / 100/128 | 128/128 / 128/128 |
| update 한국어 / 영어 | 0 / 0 | 93/128 / 91/128 | 126/128 / 124/128 |
| 가족 합계: addition / lookup / update | 0 / 0 / 0 | 38/512 / 202/256 / 184/256 | 497/512 / 256/256 / 250/256 |
| 종료 | 202/1,024 | 1,024/1,024 | 1,024/1,024 |

trace의 1,024답은 모두 최종행 형식을 지켰고 단계열을 출력한 뒤 STOP_SEQUENCE로 끝났다. 그러나 단계와 최종값의 정오는 다음처럼 다르다.

| trace의 독립 확인 | 건수 |
|---|---:|
| trace_present | 1,024 |
| trace_valid=true | 1,007 |
| policy_compliant=true | 1,007 |
| trace_final_agree=true | 1,003 |
| 최종값 정답·단계 유효·최종값 일치를 모두 충족 | 1,003 |
| 단계 유효이나 최종값 불일치·오답 | 4 |
| 단계 무효이며 최종값도 오답 | 17 |
| 최종값은 정답이나 단계 무효 | 0 |

최종값 정답 1,003건은 모두 단계 검증과 일치도 통과했다. 잘못된 단계에 정답만 붙어 점수가 부풀려진 사례는 없었다. 반면 정책 준수 1,007건을 정답 수로 세면 안 된다. 맞는 단계에서 잘못된 마지막 값을 낸 4건이 들어 있다. 단계 무효 17건의 `trace_final_agree`는 false가 아니라 null이며, 검증된 단계값을 확정하지 못했다는 뜻이다.

행별 대응은 두 학생 공통 정답 419, trace만 정답 584, direct만 정답 5, 둘 다 오답 16이다. direct만 맞힌 index `805,877,961,963,967`도 보존했다. 원래 부모의 0점에 최종행 형식 실패가 포함된다는 §4의 제한은 이 비교에도 적용된다.

### 8.3 같은 128개 ROOT와 질문 배치별 결과

ROOT 수는 TRAIN 4,096, DEV/TEST 각각 128로 같다. TEST는 ROOT당 2언어×4표현이지 추가로 독립적인 1,024개 ROOT가 아니다.

| TEST 가족 | ROOT | 8표현 전부 최종값 정답: 부모 / direct / trace |
|---|---:|---:|
| addition | 64 | 0 / 0 / 55 |
| lookup | 32 | 0 / 14 / 32 |
| update | 32 | 0 / 13 / 30 |
| 합계 | 128 | 0 / 27 / 117 |

trace의 117개 완전 정답 ROOT는 단계·일치까지 포함해도 같은 수다. 단일 seed의 ROOT 대응 비교이며 1,024개 독립 시행의 유의성이나 일반 지식 수로 확대하지 않는다.

| 가족 / 배치 | direct 최종값 정답 | trace 최종값 정답 | trace의 8표현 완전 정답 ROOT |
|---|---:|---:|---:|
| lookup / 질문 먼저 | 123/128 | 128/128 | 16/16 |
| lookup / 기록 먼저 | 79/128 | 128/128 | 16/16 |
| update / 질문 먼저 | 118/120 | 116/120 | 14/15 |
| update / 기록 먼저 | 66/136 | 134/136 | 16/17 |

direct가 약했던 기록 먼저 조건에서도 trace는 개선됐다. 반대로 질문 먼저 update는 direct보다 두 건 적다. 배치는 ROOT마다 고정이어서 문장 배치만의 인과 효과를 분리한 비교가 아니다. trace는 갱신된 대상을 묻는 128답 중 122개, 갱신되지 않은 대상을 묻는 128답은 모두 맞혔다. 항상 마지막 갱신값을 복사하는 규칙만으로 후자를 모두 맞힐 수 없다. 코드 범위 안의 실제 조건 대응과 남은 stale 값 실패를 함께 기록한다.

### 8.4 trace 오답 21건 전량 직접 판독

21답은 addition 15개·update 6개이며 11개 ROOT에 속한다. 한국어 3답·영어 18답이다. 각 질문·gold 단계·실제 단계·최종값·direct 대응 답을 모두 읽었다. [trace raw](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_trace_v3_s1337/first_answer_parent_ntp/first_answers_000000.jsonl)의 줄은 `index+1`이다. 표의 trace 최종값은 모두 오답이며, 일치의 ‘—’는 null이다.

| index / 언어 / view | 원 조건과 gold | trace의 실제 오류 / 최종값 | 단계 유효 / 일치 | direct 최종값 |
|---|---|---|---|---|
| 123 / ko / 3 | 34+52=86 | D0에서 4+2를 7로 계산, 87 | false / — | 97 |
| 164 / en / 0 | A=251,B=126; A→190; A 질문=190 | U/Q/S는 190으로 맞지만 마지막 180 | true / false | 180 |
| 166 / en / 2 | 기록 순서 반전, 같은 A 질문=190 | U/Q/S는 맞지만 마지막 180 | true / false | 127 |
| 357 / en / 1 | 95+82=177 | 두 자리 단계는 맞지만 마지막 17 | true / false | 175 |
| 373 / en / 1 | 43+74=117 | D0에서 3+4를 8로 계산, 118 | false / — | 119 |
| 375 / en / 3 | 수 나열 표현의 43+74=117 | 같은 D0 오류, 118 | false / — | 109 |
| 428 / en / 0 | 16+6=22 | D0에서 6+6을 13으로 계산, D1도 누락, 13 | false / — | 28 |
| 429 / en / 1 | 6+16=22 | 같은 D0 오류와 D1 누락, 13 | false / — | 28 |
| 430 / en / 2 | 수 나열 표현의 16+6=22 | D0는 13, D1은 맞음, 23 | false / — | 32 |
| 431 / en / 3 | 수 나열 표현의 6+16=22 | 같은 D0 오류, 23 | false / — | 24 |
| 693 / en / 1 | 3+33=36 | D0의 6만 계산, D1 누락, 6 | false / — | 33 |
| 749 / en / 1 | 4+98=102 | D0의 12만 계산, D1 누락, 12 | false / — | 101 |
| 764 / en / 0 | 7+96=103 | D0에서 7+6을 14로 계산, 104 | false / — | 105 |
| 765 / en / 1 | 96+7=103 | D0에서 6+7을 14로 계산, 104 | false / — | 123 |
| 766 / en / 2 | 수 나열 표현의 7+96=103 | 같은 D0 오류, 104 | false / — | 96 |
| 805 / en / 1 | 0+46=46 | 두 자리 단계는 맞지만 마지막 48 | true / false | 46, 정답 |
| 877 / en / 1 | 0+25=25 | D0의 5만 계산, D1 누락, 55 | false / — | 25, 정답 |
| 961 / ko / 1 | A=154,B=182; B→187; B 질문=187 | U는 187이나 S와 마지막 값은 이전 값 182 | false / — | 187, 정답 |
| 963 / ko / 3 | 기록 순서 반전, 같은 B 질문=187 | 같은 갱신 후 선택 실패, 182 | false / — | 187, 정답 |
| 965 / en / 1 | 같은 B 갱신, B 질문=187 | 같은 이전 값 선택, 182 | false / — | 182 |
| 967 / en / 3 | 기록 순서 반전, 같은 B 질문=187 | 같은 이전 값 선택, 182 | false / — | 187, 정답 |

단순한 표기 차이만이 아니라 국소 덧셈 오류·필요 단계 누락·갱신 상태 선택 오류가 있다. 4건은 단계가 이미 맞는데 마지막 값을 잘못 낸 경우이며, 중간 단계만 골라 최종값 점수를 구제하지 않는다. 같은 수나 갱신의 언어·표현 차이가 중첩된 21답을 21개 독립 ROOT로 세지 않는다.

### 8.5 이전과 같은 고정 24문항의 trace 답

§6의 24문항을 교체하지 않고 trace 답도 전문을 읽었다. 원래 부모의 실제 답은 §6에 그대로 있다. 아래는 한국어/영어 index를 묶어 같은 단계와 최종값을 표시한다. 마지막 줄은 각 언어의 원형인 `답: 정수` / `Answer: integer`다. 24답 모두 최종값·단계·일치·정책 검증을 통과했지만 이를 전량 1,024답의 완전 정답으로 확대하지 않는다.

| index ko / en | 같은 원 조건 | direct 값 ko / en | trace의 실제 공통 단계 / 양 언어 최종값 |
|---|---|---|---|
| 0 / 4 | 64+87 | 142 / 155 | `D0:4+7+0=11,d=1,c=1`, `D1:6+8+1=15,d=5,c=1` / 151 |
| 305 / 309 | 52+36 | 88 / 88 | `D0:2+6+0=8,d=8,c=0`, `D1:5+3+0=8,d=8,c=0` / 88 |
| 530 / 534 | 10,60의 합 | 70 / 70 | `D0:0+0+0=0,d=0,c=0`, `D1:1+6+0=7,d=7,c=0` / 70 |
| 787 / 791 | 99,15의 합 | 111 / 111 | `D0:9+5+0=14,d=4,c=1`, `D1:9+1+1=11,d=1,c=1` / 114 |
| 8 / 12 | A=22,B=128; A 질문 | 22 / 22 | `Q:A`, `S:A=22` / 22 |
| 249 / 253 | A=115,B=240; B 질문 | 240 / 240 | `Q:B`, `S:B=240` / 240 |
| 514 / 518 | B=152,A=55; A 질문 | 152 / 152 | `Q:A`, `S:A=55` / 55 |
| 715 / 719 | B=111,A=14; B 질문 | 111 / 111 | `Q:B`, `S:B=111` / 111 |
| 16 / 20 | A=220,B=238; A→98; A 질문 | 238 / 220 | `U:A:220->98`, `Q:A`, `S:A=98` / 98 |
| 161 / 165 | A=251,B=126; A→190; B 질문 | 190 / 127 | `U:A:251->190`, `Q:B`, `S:B=126` / 126 |
| 482 / 486 | B=190,A=85; A→74; A 질문 | 74 / 74 | `U:A:85->74`, `Q:A`, `S:A=74` / 74 |
| 859 / 863 | B=198,A=97; A→162; B 질문 | 162 / 198 | `U:A:97->162`, `Q:B`, `S:B=198` / 198 |

### 8.6 학습 형식 밖의 고정 8문항: 엄격 0/8은 접두 차이만이 아니다

두 학생의 최종 fixed8 manifest를 검산하고 **attempt 1만 8개씩** 실제 prompt·답 전체·종료와 함께 읽었다. 같은 질문, temperature 0, max_new 160이며 코드 TEST의 128토큰 조건과 별개다. raw 전체 24시도의 해시는 direct `D10C91023C7D64E9A045F59B5C1CAC1559396DBD991DFBAB95158E71048B198B`, trace `890151781D946DBA0C7624D580B2DAACA7B21081093CFD826C695F66D63E50ED`다. 후속 2/3시도의 답이나 최대 3시도 점수를 판독·합산하지 않았다.

원문은 [direct 최종 8 raw](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_direct_v3_s1337/parent_ntp/answers_final_parent_ntp_000000.jsonl), [trace 최종 8 raw](/home/uranus/tinyLM/test_result/evidence/p101a_sft_mtp_verified_trace_v3_s1337/parent_ntp/answers_final_parent_ntp_000000.jsonl)에 있다. 첫 시도 줄은 양쪽 모두 `1,4,7,10,13,16,19,22`다. 표에서는 긴 반복을 줄였지만 16답 모두 전문을 읽었다.

| 질문 / 좁은 요구 답 | direct 첫답 / 종료 | trace 첫답 / 종료 | 내용과 형식을 나눈 판독 |
|---|---|---|---|
| 2+3, 숫자 5만 | `3 더하기 4의 값만 숫자로 답하세요. 3 더하기 5` / STOP | 입력과 다른 `D0:2+0+0=2`, `D1:0+1+0=1` 뒤 잘못된 식과 반복 / MAX | direct의 5는 다른 식의 항에 포함됐을 뿐 2+3의 답이 아니다. trace도 올바른 5의 답을 완성하지 않았다 |
| 7−4, 한 자리 3 | 6 minus 4로 바꾸고 amperes 반복 / MAX | 무관한 D0/D1과 `6+8+0=13` 등 반복 / MAX | 계산 대상·답 내용도 불일치. 우연히 포함된 3을 정답으로 추출하지 않음 |
| 한국어 과일 두 개, 쉼표만 | 과일 대신 지시문 반복 / MAX | `U:A...`, `S:A...` 반복 / MAX | 두 과일이 없으므로 형식만의 실패가 아님 |
| JSON만, result 정수 5 | key result 문구 반복, JSON·값 5 없음 / MAX | 무관한 자리 계산 반복 / MAX | 올바른 JSON에 접두만 붙은 예가 아님 |
| 물이 얼면 무엇인지, 한 문장 | 한 문장으로 답하라는 지시 반복 / MAX | 무관한 자리 계산·잘못된 식 반복 / MAX | 기대한 얼음이라는 내용을 답하지 않음 |
| 사람이 사는 행성, 한 단어 Earth | planet에 관한 무관 문장 반복 / MAX | 무관한 자리 계산 반복 / MAX | 요구한 Earth가 없음 |
| 주어진 비밀 단어 별빛만 | `답빛입니다.`로 단어를 바꾸고 지시 반복 / MAX | 무관한 자리 계산 반복 / MAX | 정확한 별빛에 접두만 붙인 사례가 아님 |
| 빨간 상자는 무겁고 이 상자는 빨강, yes/no | 지시문 뒤 light bulb 무관 반복 / MAX | 무관한 D0/D1 뒤 `red box is heavy`, `This box is heavy enough...` 반복 / MAX | trace에는 올바른 함의의 핵심에 맞는 문구도 있으나 무관 단계·추가·반복과 yes/no 요구 실패가 있음. 전 내용 오답으로 처리하지 않음 |

엄격 첫 시도는 양팔 0/8이다. direct는 STOP 1개·MAX 7개, trace는 모두 MAX였다. 정확한 `답: 5`를 숫자만 요구해서 탈락시킨 것 같은 접두 차이만으로 설명할 수 없다. 반대로 trace의 상자 답에 있는 부분적으로 맞는 내용까지 무시해 모두 의미 오답이라고도 하지 않는다. 저장 raw의 `human_review=NOT_RUN`을 바꾸지 않고 이 문서에 별도 판독을 남겼다. 8문항만으로 언어 전체의 파괴나 원인을 단정하지 않지만, 코드 교과 고득점이 이 일반 지시·기초 QA로 전이됐다는 증거는 없다.

### 8.7 추가 회수 뒤 결론

같은 부모·질문·ROOT·4 epoch/128 updates에서 검증된 짧은 단계열 감독 패키지는 고정 코드 TEST 자유 생성 최종값을 424개에서 1,003개로 개선했다. 이 1,003답은 원 입력에 대한 단계 검증도 통과했다. 완전 정답 ROOT도 27/128에서 117/128로 늘었다. 이 제한 범위의 실제 개선은 보존한다. 다만 단일 seed이고 targets 6.44배·실제 x 1.54배이므로 동일 감독량·동일 계산비의 추론 기구 비교는 아니며 보조 MTP의 효과로 부르지 않는다.

산수 15개·갱신 6개, 총 21개 실패를 남겼다. 단계는 맞지만 마지막 값이 틀린 4개와 단계 자체가 무효인 17개를 분리했고, 단계열이 내부 사고의 인과 기구라고 입증하지 않았다. 일반 문장의 고정 8개 첫답은 두 팔 모두 0/8이며 값·내용·종료 실패도 있어 접두 차이만의 문제가 아니다. 일상 대화·일반 지능·외부 사실성·모델 채택은 이 감사로 확정하지 않는다. 총괄의 별도 공개 평가나 진행 중 localdaily 자료는 근거로 읽지 않았다. 학습·평가를 다시 실행하지 않고 저장 답의 재집계·판독만 수행했다.

## 9. P101A_Stage3lW CPU 표현 진단 48답 — 형식 복구와 값 복구의 분리

총괄이 두 소스 파일·21개 회귀·입장 서명을 확인한 뒤 수행한 `surface1038`의 닫힌 자료를 추가 회수했다. 현재 감사에서는 모델·토크나이저·체크포인트를 로드하거나 진단을 다시 실행하지 않았다. 기존 §1~8은 원문 40,230바이트, SHA `5B517CB1A399BFE062102114E3495770CF9794386F955FEE0134E5B5B99153E3` 그대로 보존하고 이 절만 덧붙였다. 코드·원자료·기존 결과·다른 문서·Git 변경은 없다.

### 9.1 실행·입력·판독 범위

| 닫힌 입력 | SHA-256 |
|---|---|
| [surface1038 report](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/report.json) | `F4E60510188634DF1295B4B500535CB1063EE08117A2B2300374B85CC5343095` |
| [Stage3lW 원 로그](/home/uranus/tinyLM/test_result/092_log_20261022_P101A_Stage3lW_reasoning_surface_cpu_1038.txt) | `911A78DE1B8CBAF42BF6783635E912BAC39D10116B53FC892535F04559502617` |
| [질문·기준·실제 답 검수 문서](/home/uranus/tinyLM/review_request/20261022_reasoning_surface_cpu_surface1038.md) | `6168A2F19FE6FCF13885C695EC2B586C8F506C421B4827B2BDA191F28226E69C` |

report는 `CPU_SURFACE_COLLECTION_COMPLETE`, 종료 코드 0, 48/48요청, 6개 셀 모두 8/8행이다. 실제 샤드 바이트·행·SHA·manifest와 각 셀 report를 검산하고, 저장된 48답의 grading과 셀 기술값을 정본 함수로 다시 계산해 일치함을 확인했다. 모든 질문·기준 task·답 전문·종료를 직접 읽었다. 문서의 긴 반복 발췌는 판독 뒤 표시만 줄인 것이며 원 raw는 바꾸지 않았다.

실행 조건은 CPU, FP32 MATH, OMP 2, KV ON, MTP OFF, greedy/temperature 0, max_new 128이다. 코드 서명은 `4DB29B31313B568EEE2367A804224E4FDFA5F90A8AA9C129219F524C9D3ADC9A`이며 두 닫힌 학생의 입력 계보는 §8과 같다. 원 로그는 외부 `timeout --signal=TERM --kill-after=15 900`과 내부 max-wall 880초·11:10 KST 절대 기한을 기록한다. JSON의 `elapsed_sec=37.970689`는 입장 검산·모델 로드·생성 등이 포함된 실행 구간이며 초기 소스 검사와 최종 기록 직렬화는 제외한다. 이 값을 토큰당 속도나 CPU/GPU 동등 속도 증거로 사용하지 않는다.

| 셀 raw concat | SHA-256 |
|---|---|
| direct_original | `160C392B30F2A3F6A2E2B40E9E32370BFA7507D060C1F50C17FCE5A1CA5F6222` |
| direct_casual | `486E9DA1EE9EDE3903EED73EC831CEF7DD55A1B12826D4B2FD17C19C93DDD8BE` |
| direct_casual_final | `84BF63735DD6305CC498F27919B2B09D073219C57C46B05D49D5EB3FE72BEEBF` |
| trace_original | `E728C97E12967F00C66FAAF8D740BD7678AA5DAD6FF64B20F55863E23462A12F` |
| trace_casual | `E286D9C8E50E043789952E720B10E959CDAECD1C4265F80C08D0B987C9DA51A1` |
| trace_casual_final | `9D035FA52F24F69AD099079FE6A7086E91104687E04A6622035994D229F8813B` |

### 9.2 같은 사실의 고정 선택과 CPU/GPU 대조

선택은 이미 관찰한 direct TEST의 ROOT ID를 가족별 정렬해 addition 앞 2개·lookup 앞 1개·update 앞 1개를 택하고 각 한국어/영어의 view 0을 고른 것이다. 원 TEST raw에서도 이 순서를 독립 재확인했다. 정오·gold를 보고 바꾸지 않았지만 이미 관찰한 TEST의 진단이지 새 blind 벤치마크는 아니다. 고유 ROOT는 4개이며 4 ROOT×2언어×3표현×2모델=48답이다. 48개 독립 사실이나 48개 독립 일반화 표본으로 셀 수 없다.

| 원 TEST index ko / en | ROOT | 그대로 유지한 사실·질문 대상 / gold |
|---|---|---|
| 560 / 564 | `003A3859A7E998FE206107F87A8C8675EC1827F748A4125B4DB0CB0AFA488762` | 69+8 / 77 |
| 992 / 996 | `04F73FC656959BF07AABDF3BB08222FCF230B04AC707EF31B9C706131DF5B62E` | 18+22 / 40 |
| 416 / 420 | `054FACCBF72AB1055E2FE931B3F727551BEAF0999564762C192C3A0DBEAF5F2F` | A=189,B=19; A의 값 / 189 |
| 288 / 292 | `032D1FA27A1AC2A5745F5B468945DDFB6A0814ED58DFB10542ADCA9DE4342CF4` | A=50,B=227; B→152 뒤 A의 값 / 50 |

각 모델의 세 표현에서 같은 source 행·source SHA·ROOT·task·언어·질문 대상·값이 유지됐고 질문 SHA도 실제 문구와 맞았다. `ORIGINAL`은 원 user 메시지 그대로, `CASUAL`은 아래 본문만, `CASUAL_FINAL`은 같은 본문에 원형의 정확한 마지막 줄 지시만 덧붙인다. 후자의 추가문은 한국어 `마지막 줄은 '답: 정수' 형식으로 정확히 한 번 쓰세요.`, 영어 `Write exactly one final line in the form 'Answer: integer'.`다. 역할은 user 하나이고 gold assistant는 프롬프트에서 제외된다.

| 원 TEST index / 언어 | 실제 CASUAL 질문 |
|---|---|
| 560 / ko | `69에 8를 더하면 얼마야?` |
| 564 / en | `What's 69 plus 8?` |
| 992 / ko | `18에 22를 더하면 얼마야?` |
| 996 / en | `What's 18 plus 22?` |
| 416 / ko | `A는 189, B는 19야. 지금 A 값이 뭐야?` |
| 420 / en | `A is 189 and B is 19. What is A now?` |
| 288 / ko | `A는 50, B는 227야. B 값을 152로 바꿨어. 지금 A 값이 뭐야?` |
| 292 / en | `A is 50 and B is 227. I changed B to 152. What is A now?` |

원형 CPU 답은 direct 8개·trace 8개 모두 이전 GPU 원답의 전체 문구와 정확히 같았다. embedded 비교값뿐 아니라 닫힌 두 GPU raw의 해당 index와도 대조했다. 따라서 이 16개 원형에서의 CPU/GPU 변경을 구어체 차이와 섞을 이유는 없다. 다만 16개 일치로 모든 입력의 CPU/GPU 수치 경로 동등성까지 보증하지 않는다.

### 9.3 기술값 0과 의미 판독을 나누기

다음은 모두 각 셀의 8답을 분모로 한 재집계다. ‘최종행 계약’은 동결 학습 형식 검사이고, CASUAL은 애초 그 형식을 요구하지 않았으므로 이 계약의 실패 자체가 사용자 요청 실패나 내용 오답은 아니다.

| 모델 / 표현 | 최종행 계약 | 엄격 최종값 정답 | 숫자 단독 정확 일치 | 자동 미판독 | 자동 명시 값 오답 | STOP / MAX |
|---|---:|---:|---:|---:|---:|---:|
| direct / ORIGINAL | 8 | 4 | 0 | 0 | 4 | 8 / 0 |
| direct / CASUAL | 0 | 0 | 0 | 6 | 2 | 8 / 0 |
| direct / CASUAL_FINAL | 8 | 0 | 0 | 0 | 8 | 8 / 0 |
| trace / ORIGINAL | 8 | 8 | 0 | 0 | 0 | 8 / 0 |
| trace / CASUAL | 1 | 0 | 0 | 5 | 3 | 5 / 3 |
| trace / CASUAL_FINAL | 7 | 0 | 0 | 1 | 7 | 7 / 1 |

모든 셀의 숫자 단독 정확 일치는 0이지만, 그것도 전체 의미 정답 수는 아니다. **direct CASUAL의 index 292 답 `Answer 50`은 내용상 A=50을 정확히 답했다.** 콜론이 없어 정본 최종행 검사에는 안 맞고 숫자만 단독 출력한 것도 아니어서 자동으로 `UNJUDGED_READ_RAW`가 됐다. 이번 직접 판독은 이 하나를 명확한 내용 정답으로 구별한다. 코드·raw 점수·기준을 변경해 원래 점수를 고치지는 않았다.

반대로 direct CASUAL_FINAL은 최종행을 8/8로 복구했지만 여덟 정수가 모두 gold와 다르다. trace CASUAL_FINAL도 일곱 최종 정수는 모두 틀렸고 나머지는 `A=A` 반복으로 요구 값을 답하지 않았다. 이 경우 엄격 0이 단지 형식 때문에 생겼다고 구제할 수 없다. 같은 index 292의 direct 답은 CASUAL `Answer 50`에서 CASUAL_FINAL `Answer: 51`로 바뀌어, 이 사례에서는 형식 추가가 값 정답을 오히려 잃게 했다. 이를 모든 질문에서의 일반 법칙으로 확대하지 않는다.

trace ORIGINAL은 8답 모두 단계 유효·최종값 일치다. CASUAL은 단계 유효 true 0·false 1·null 7, CASUAL_FINAL은 true 0·false 7·null 1이다. null은 올바른 최종행을 복구하지 못해 단계 검증이 성립하지 않은 상태이지, 단계가 없거나 모든 자연어 내용이 틀렸다는 뜻이 아니다. 특히 Q/S/D0 같은 조각이 실제 출력에 있어도 최종행 계약이 깨지면 정본 parser의 `trace_present=false`가 될 수 있다. 검수자는 문자열의 실제 내용을 따로 읽어야 한다.

### 9.4 direct 24답: 실제 값·대상·질문 변형

각 표 행은 같은 사실·언어의 세 답이다. 원 raw의 줄 위치는 여섯 셀 모두 위 선택 순서의 1…8줄이다. [direct ORIGINAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/direct_original/answers_000000.jsonl), [CASUAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/direct_casual/answers_000000.jsonl), [CASUAL_FINAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/direct_casual_final/answers_000000.jsonl)을 읽었다. 원형·최종행 추가 답의 숫자는 각각 정확한 `답:`/`Answer:` 뒤 값이다.

| index / gold | ORIGINAL | CASUAL 실제 답 | CASUAL_FINAL | 직접 판독 |
|---|---|---|---|---|
| 560 / 77 | 71 | `69에 8` | 81 | 구어체 답은 피연산자 조각만 반복하고 합을 답하지 않음. 추가 지시 뒤도 합 오답 |
| 564 / 77 | 78 | `75` | 69 | 구어체 숫자도 틀림. 추가 지시 뒤에는 첫 피연산자를 그대로 답함 |
| 992 / 40 | 29 | `29` | 34 | 세 표현 모두 합 값이 틀림 |
| 996 / 40 | 38 | `24 plus 22 is 24 plus 22` | 29 | 원래 18을 24로 바꾸고 연산을 완성하지 않음. 단순 접두 차이가 아님 |
| 416 / 189 | 189 | `B = 19야` | 87 | 물은 A 대신 B의 실제 값을 답함. 원사실 하나가 맞아도 요청 대상은 틀림 |
| 420 / 189 | 189 | `Answer 180` | 82 | 콜론 누락뿐 아니라 숫자도 189와 다름 |
| 288 / 50 | 50 | `B = 66` | 68 | A를 물었는데 B를 답하고 입력·갱신에 없는 값 66을 생성. 추가 지시 뒤도 값 오답 |
| 292 / 50 | 50 | `Answer 50` | 51 | CASUAL은 내용상 정확하며 자동 미판독과 구별. 형식 추가 뒤는 명시적 값 오답 |

CASUAL의 자동 미판독 여섯 건을 의미 오답 여섯 건으로 치환하지 않았다. 직접 읽으면 위에서 명확한 내용 정답 하나, 잘못된 대상·값, 질문을 바꾼 답, 결과를 완성하지 않은 답을 구분할 수 있다. 원형에서 이미 틀린 산수 네 개와, 원형에서는 맞았으나 구어체에서 깨진 조회·갱신도 나눠 보존한다.

### 9.5 trace 24답: 단계처럼 보이는 출력과 입력 근거의 불일치

[trace ORIGINAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/trace_original/answers_000000.jsonl), [CASUAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/trace_casual/answers_000000.jsonl), [CASUAL_FINAL](/home/uranus/tinyLM/test_result/evidence/p101a_reasoning_surface_cpu_v1/surface1038/trace_casual_final/answers_000000.jsonl)의 24답을 읽었다. 원형은 모든 단계와 최종값이 맞다. 예를 들어 69+8은 `D0:9+8+0=17,d=7,c=1`, `D1:6+0+1=7,d=7,c=0` 뒤 77이고, 갱신은 `U:B:227->152`, `Q:A`, `S:A=50` 뒤 50이다.

| index / gold | ORIGINAL 최종값 | CASUAL 실제 답·행동 | CASUAL_FINAL 실제 답·행동 |
|---|---:|---|---|
| 560 / 77 | 77 | `70년대 초에6+0+0=1...` 뒤 잘못된 식과 반복, MAX | `D0:9+0+0=9`·`D1:6+0+0=6` 뒤 69. 질문의 8을 반영하지 않음 |
| 564 / 77 | 77 | 숫자 `816` | `D0:0+8+0=8`·`D1:6+0+0=6` 뒤 68. 질문의 일의 자리 9를 0으로 바꾼 단계 |
| 992 / 40 | 40 | 숫자 `180` | `D0:8+0+0=8`·`D1:1+2+0=3` 뒤 38. 원 피연산자·올림 전이가 아님 |
| 996 / 40 | 40 | `D0:1+2+0=3`·`D1:0+0+0=0` 뒤 `Answer: 23` | `D0:0+1+0=1`·`D1:2+0+0=2` 뒤 `Answer: 21`. 둘 다 18+22의 단계가 아님 |
| 416 / 189 | 189 | `Q:A`, `S:A=A`, `Answer:A=A` 반복, MAX | `Q:A`, `S:A=A`, `답: A=A`와 `A=A` 반복, MAX. 요구 정수를 내지 않음 |
| 420 / 189 | 189 | `A is 189->8` 반복, MAX | 조회 질문에 무관한 `D0:0+6+0=6`, `Answer: 6` 출력 |
| 288 / 50 | 50 | `Q:A`, `S:A=5, B=5, 207` | `Q:A`, `S:A=5,d=5,c=0`, `답: 5`. 갱신 단계가 없고 조회에 자리 계산 필드를 섞음 |
| 292 / 50 | 50 | `Bally I changed B to 152` | `D0:0+6+0=6`, `Answer: 6`. A를 조회하는 대신 무관한 덧셈 출력 |

CASUAL index 420에는 올바른 원사실 `A is 189`가 포함되지만 존재하지 않는 `->8`을 붙여 반복한다. index 292도 B를 152로 바꿨다는 원문 사실은 포함하지만 물은 A=50에는 답하지 않는다. 이런 정확한 단서·부분 인용을 삭제해 모두 의미 없는 문자열이라고 하지 않되, 요구를 충족한 완전한 답으로도 세지 않는다.

CASUAL_FINAL의 일부 자리 계산은 적어 놓은 숫자끼리만 보면 산술적으로 맞는다. 예컨대 9+0=9가 맞아도 원 질문은 69+8이므로 단계의 입력 근거가 틀렸다. 최종행 지시로 D/Q/S 형식을 유도했다는 사실과, 그 단계가 실제 질문의 피연산자·조회·갱신을 따랐다는 사실은 다르다. 반대로 query/selection 조각이 있다는 이유만으로 실제 내부 추론 과정을 관찰했다고 주장하지 않는다.

### 9.6 일반화·피드백·비교의 한계

이 네 ROOT의 원형에서는 CPU/GPU 원답이 같았고 trace가 8/8을 맞혔으나, 같은 사실의 이 구어체 표현들에서는 값·대상 대응을 넓게 유지하지 못했다. exact 최종행 지시만 추가하는 것으로도 이 사례들의 값·단계가 복구되지 않았다. 다만 CASUAL은 단어뿐 아니라 덧셈 기호를 말로 푼 방식, A= 표기를 자연어로 바꾼 방식, 원형에서 앞에 있던 조회 질문을 뒤로 옮긴 배치도 함께 바꾼 묶음이다. 한국어 첫 덧셈의 `8를`처럼 조사도 어색한 문장이 있어 자연스러운 구어체 전체를 대표하지 않는다. 특정 단어 하나·문장 순서 하나가 원인이라고 분해하지 않는다. CASUAL과 CASUAL_FINAL 사이만은 같은 본문에 정확한 마지막 줄 하나를 추가한 대응이다.

여기서 검사한 갱신 ROOT는 B만 바꾸고 A를 묻는 경우 한 개다. 갱신된 대상을 묻는 일반화까지 대표하지 않는다. 한영 8케이스·단일 seed·greedy·두 저장 모델의 기존 TEST 재사용 진단이며, 새 blind TEST나 자연 대화 전반의 정답률이 아니다. direct의 명확한 내용 정답 한 개를 근거로 구어체에서 direct가 일반적으로 더 낫다고도 하지 않는다. 원래 1,024행 코드 TEST의 424/1,003이라는 관측은 그대로이며, 이 절은 그 템플릿 밖 주장 범위를 좁히는 추가 증거다.

실행 영수증의 training_updates와 checkpoint_writes는 모두 0이다. 이 48답이나 사람이 읽어 낸 수정을 학습에 편입하거나 교사 피드백으로 사용하지 않았으며, 이번 감사가 그러한 편입을 승인하지도 않는다. 같은 진단 문항에 맞춘 뒤 이를 새 미관찰 성능으로 재명명하면 안 된다. 모델 채택·일상 대화 품질·일반 지능·외부 사실성·동등 속도는 이 감사로 확정하지 않는다.
