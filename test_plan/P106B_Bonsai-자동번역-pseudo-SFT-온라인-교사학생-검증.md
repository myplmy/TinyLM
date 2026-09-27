# P106B — Bonsai 자동번역 pseudo-label SFT와 온라인 교사·학생 연결 검증

> 제안 계기: 사용자 2026-09-27 지시와 추가 질문. [P106 검증형 교사 계약](P106_검증형-교사-정답-계보와-SFT-첫게이트.md)은 독립 검증된 정답만 `ACCEPT`로 부른다. **일반 SFT 데이터가 모두 참이라는 보증은 없고, 전수 사람 승인은 기술적 학습의 필요조건이 아니다.** 이 계획은 P106의 검증형 주장·기존 결과를 고치지 않는 별도 `B` 축이다. 교사 자동번역을 곧바로 학습에 쓸 수 있는지 한정 실험하되 이를 `PSEUDO_UNVERIFIED`로 표시한다.

## 1. 왜 — 질문을 두 개로 나눈다

[결과098 §8](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)의 full-GPU Bonsai+P076 모양 학생 두 팔은 **합성 입력 2업데이트 자원공존**만 확인했다. 실제 교사 문자열이 학생의 canonical ChatML assistant-only 손실로 들어간 증거는 0이다. [공개 SFT 적격성 결과096 §10](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)는 전체 공개 v3의 `TRAIN_READY=false`를 보존한다. 그렇다고 모든 교사 번역을 사람이 전수 승인할 때까지 **별도 소형 pseudo-label 기능 실험조차 금지할 근거는 없다.**

이 계획은 먼저 `교사 출력 → 자동 형식/민감정보 필터 → 학생 loss`가 실제로 작동하는지만 잰다. 그 뒤 한국어 대화·지식 향상을 주장하려면 원답/번역 정합·오염·동일 부모 대조와 독립 평가가 별도로 필요하다. 교사 자신의 답이나 `verifier_origin` 필드만으로 진실을 보증하지 않는다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 고정 OASST2 영어 단일턴을 Bonsai 2 27B가 구조화된 한국어 질문·답으로 시간·VRAM 한도 안에 바꿀 수 있는가 | 27B는 thinking 모델이라 짧은 출력상한이면 답이 중간에 끊길 수 있음 |
| Q2 | 검증되지 않은 번역을 `ACCEPT`로 오기하지 않고도 P076의 legacy32 학생에 assistant-only SFT 손실이 흐르는가 | 사용자가 요구한 직접 교사→학생 교육의 첫 실동작 |
| Q3 | micro8×accum16/activation-checkpoint ON으로 full 교사와 공존하며 적어도 2업데이트를 끝내는가 | 종전 합성 토큰·ctx512 gate를 실문장·ctx1024로 확장 |
| Q4 | 작은 자동 번역 pilot의 출처·중복·오류율·비용이 어느 정도인가 | 본학습/품질 승격의 선결; 한 팔의 CE 하락은 지능 개선 아님 |
| Q5 | 같은 고정 문항에서 기존 P076 학생과 pseudo-SFT 후 학생의 정답·오답 유형은 어떻게 바뀌는가 | 교사 학습 결과를 원답안·문항별 회귀로 직접 확인하되 교사 단독 인과와 구분 |

## 3. ★예측 — 성공과 실패를 둘 다 등록

- 구조화 한국어 번역이 일부 가능하고 학생 손실 배선은 통과할 수 있다. 그러나 공식 [Bonsai 2 안내](https://github.com/PrismML-Eng/Bonsai-demo#thinking)는 사고 토큰이 먼저 나오는 모델이라, `max_tokens=768`/ctx1024/medium에서도 완성 JSON 비율이 낮거나 비용이 클 수 있다. 이 경우 `exit8`은 유효한 제한조건 음성이지 코드 오류가 아니다.
- 독립 검증 없이 번역을 바로 학습하면 문맥 생략·잘못된 번역·의미 추가가 학생에 전달될 수 있다. 이는 **금지할 수밖에 없는 실행 오류가 아니라 측정·관리할 데이터 소음**이다. 따라서 자동 구조·PII/숫자 보존 필터, 원문/번역 별도 저장, 사후 표본검토를 두되 0% 오류를 주장하지 않는다.
- 16개의 짧은 대화를 반복해 2업데이트하는 Stage1b는 배선·VRAM·비용만 측정한다. 고유 진단 체크포인트를 남기고 Stage1c에서 같은 공개 문항을 재평가하더라도, 작은 노출에 따른 큰 분산/망각 때문에 지능 향상을 예측하거나 주장하지 않는다.

## 4. 단계 설계 — 싼 것부터

### Stage0W — 공개 OASST2 한정 선별/비보호 CPU 게이트(코드 작성, 실자료 check-only)

[선별·교사 게이트](../scripts/diag_p106_oasst2_teacher_ko_gate.py)는 pinned [OASST2 카드](https://huggingface.co/datasets/OpenAssistant/oasst2) Apache-2.0 표기·고정 원본 SHA `7A886A16...B7EE29B`의 reviewed/non-synthetic 영어 **종결 단일턴** 한 경로만 선택한다. 기존 공개 v3 첫 질문 exact 겹침, 내부 중복, 원문 길이600자를 제외하고 해시순 16개를 고정한다. 현재 CPU check-only 관측: 종결 후보1326, v3 질문 겹침656, 길이 초과531, 자체 중복1, 잔존138/선정16. **외부 개별 권리·안전·의미·근사오염은 이 선별로 PASS가 되지 않는다.**

### Stage1aW — 사용자 완료·형식 음성(결과101 §1)

[역사 SH](../run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh)는 먼저 Stage0W CPU 검사 뒤 사용자 로컬 Prism build10743와 같은 SHA의 Bonsai 2 27B PTQ1_0을 **localhost 인증·offline·GPU full·GDN 융합 요청**으로 기동했다. 16개 영어 사용자/사람 답의 한 쌍을 데이터로 주고 한국어 질문·답 JSON을 요구했다. 원문과 번역 후보는 새 비보호 데이터셋 폴더 `HF/sft_ready/p106b_teacher_sft/v1/teacher_format_candidates.jsonl`에 write-once로 남겼다. 선택 문턱은 16요청 중 JSON 완성≥12, 총 wall≤1800s, 시작 free≥8192MiB, 교사 단독 적재 뒤 free≥2048MiB다. **실측 완결은9/16으로 미달·exit8**이었다([결과101 §1](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 완성된 것도 전부 `UNKNOWN`/학습 target0이며 P106 검증형 `ACCEPT`가 아니다.

### Stage1bW — 사용자 시도 완료·선결 중단, 학습 NOT_RUN(결과101 §2)

[역사 온라인 SH](../run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh)는 Stage1aW 원본/manifest의 정확 SHA와 완료 문턱을 선검사한다. **기존 학습 완료 P076 B3 mean 최종 체크포인트** `m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt`를 학생 시작점으로 선택한다(같은 구조의 dense 부모에서 다시 step0으로 시작하지 않음). legacy tokenizer SHA `3A69001E...52C48E3`를 고정하고 학생 config의 activation checkpoint를 ON으로 한 뒤 Muon RMS4×4/AdamW·bf16·CE chunk·`torch.compile(mode=default)`를 유지하도록 설계했다. 실제 실행은 상류 형식9/16 때문에 check-only에서 끝났고 학생 로딩·학습0이다.

학생을 먼저 올려 GPU 여유를 확인한 뒤 full 교사를 같은 GPU에서 ctx1024로 올린다. 교사에게 **실제로 다시 요청한** 한국어 문장 중 JSON/완료/기본 한국어·숫자·명백한 연락처 필터를 통과한 것만 별도 `PSEUDO_UNVERIFIED` 기록과 canonical assistant target으로 보낸다. 16개 중 유효 고유쌍 최소8개가 아니면 업데이트0·`exit8`. 유효쌍을 반복해 매 업데이트 `micro8×accum16=128`개 대화 노출, 총2업데이트로 제한한다. 이는 **최대 262,144 위치**(`2×8×16×1024`)의 처리 상한이지 assistant 지도토큰의 실측이 아니다. 원본 데이터/기존 checkpoint를 고치지 않고 새 runlog와 `HF/sft_ready/p106b_teacher_sft/v1/` 아래 **원문·교사출력 전체/자동 선정 canonical/각 SHA·조건 manifest를 write-once로 기록**한다. 모든 동시·loss 문턱을 지난 뒤 교사를 종료하고 고유 `runs/ckpt/m100R1c_ko-en_300M_p106b_s1b_oasst2_ko_online_s1337.pt` 진단 체크포인트 한 개만 저장한다(예상 약0.45GiB, 사용중인 기본 모델 덮어쓰기0). P100의 체크포인트·JSON 쌍 계약을 위해 같은 stem의 새 `runs/logs/*.json`도 기록하되 `final.val_loss=null`, 실제 assistant 지도토큰, `quality=NOT_RUN`으로 표시한다. 부모의 300M 예산을 이번 학습량으로 오인하지 않는다. `v1` 원본을 고치지 않고 문제행을 교정한 파생본은 `v2`로 만든다. 실제 지도토큰·유한 gradient/손실·동시 NVML/torch peak·교사 출력토큰/초·비용을 보고한다. 시작 다른 compute 앱0/free≥14GiB, 모델 공존 뒤 표본 free≥2GiB를 사전 중단선으로 둔다. `exit0`도 **기능 PASS**, 품질/`TRAIN_READY` 아님. LR `1e-4`/Muon 행렬 배수4/WD0은 SFT pilot 임시값이며 pretrain 최적 LR로 오인하지 않는다.

### Stage1aWb/Wc — 2026-09-27 절단 원인·사고/최종 분리의 짧은 대응 진단

Stage1aWb는 기본 sandbox의 NVML 차단으로 교사 적재 전 종료9였고, 별도 [Stage1aWc SH](../run_P106B_Stage1aWc_teacher_budget_attribution-done.sh)가 사용자 이번 지시 한정 **10분 이하 CPU+GPU**로 실제 완료됐다([결과101 §6~§7](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). v1의 미완결 앞3건과 완결 대조1건을 정확 원본 SHA에 묶어 같은 네 질문을 cap768/3072로 각각 한 번씩 보냈다. 두 팔 모두 `ctx4096`, `reasoning_effort=medium`, fixed seed와 [Bonsai 2 모델 카드의 thinking 샘플러](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#generation-parameters) `temperature=1.0, top_p=.95, top_k=20, min_p=.05, presence_penalty=0, repeat_penalty=1.0`을 명시하고 순서를 교차했다. **이번 팔끼리만 출력 cap 차를 귀속**한다. v1과는 ctx/샘플러도 달라 전체 개선을 cap 효과 하나로 소급하지 않는다. 8요청158.757초, cap768 완결0/4 대 cap3072 완결3/4이나 후자에서도1건은 사고문만 남기고 끝났다.

신규 `HF/sft_ready/p106b_teacher_sft/v2/`에는 네 영어 원문·`finish_reason`·행별 사용량/시간·`reasoning_content`·최종 `message.content`·파싱된 `user_ko`/`assistant_ko`를 서로 다른 필드에 write-once로 남겼다. 런로그에는 문구가 아니라 cap별 건수·길이·토큰만 남겼다. 학생으로 보낼 수 있는 필드는 **완결 최종 JSON의 `assistant_ko`뿐**이지만, 이 실행에서 실제 target 채택·학습은0이다. 사고과정·영어 사람답·불완전 fragment는 target이 아니다. 네 건은 옛 실패를 과표집하므로 **12/16 본 모집단 문턱을 통과시키지 않는다.** 사용자 선택에 따라 단순 번역 full16 대신 교정형 Stage1dW 소형 진단을 거쳐 Stage1fW 교정형 full16 후보를 준비했다. 비사고 모드와 프롬프트 축약은 기각돼 쓰지 않았다.

### Stage1dW — 교사 원답 교정 가능성과 계보 보존의 3문항 gate

Stage1aWc 짧은 대응 진단은 cap768 완결0/4·cap3072 완결3/4였지만, 완결된 WebRTC 문항에서 **원래 사람 답안의 API 오개념을 교사가 충실하게 번역**했다([결과101 §7~§8](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 사용자는 이 문제를 단순 번역이 아닌 **교사 교정안**으로 후속 시도하고, 나중에 사람이 다시 검증·개선할 수 있도록 원문과 교정본을 보존하기로 선택했다. 이는 번역형 Stage1a와 **다른 교사 작업**이며 지능 품질 증거를 합산하지 않는다.

[독립 진단](../scripts/diag_p106b_teacher_answer_repair.py)과 [Stage1dW SH](../run_P106B_Stage1dW_teacher_answer_repair-done.sh)는 v1/v2의 정확 SHA를 확인하고 세 문항만 사용했다: 원답이 `getUserMedia` 인자 타입을 틀린 WebRTC, 시점·모델 자기소개가 섞인 파라미터 수 문항, solver가 20·50으로 검산 가능한 수학 대조. 교사에게 영어 원답은 **검증되지 않은 DATA**이며 오류·시점·자기모델 주장이 있으면 수정하거나 불확실성을 답하라고 했다. 출력은 `user_ko`,`assistant_ko`,`correction_status`,`correction_note`의 완결 JSON을 요구했다. `correction_status`는 교사 자기신고일 뿐 독립 진실 판정이 아니다. `medium` + 공식 thinking sampler, `ctx6144`, `max_tokens4096`, top-level 사고 예산2048로 세 문항을 완료했다([결과101 §9](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).

`HF/sft_ready/p106b_teacher_sft/v3/`에 영어 질문/사람 원답, v1/v2 SHA, 실제 교사 사고·최종 원문, 파싱된 새 문답·교정 설명·종료/사용량을 write-once로 남긴다. **학생 학습·target 채택은0**이며 적어도2/3 JSON 완결은 형식 가능성 문턱일 뿐 내용 정답 판정이 아니다. WebRTC의 입력은 `constraints`, 반환은 `Promise<MediaStream>`이라는 [공개 API 근거](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)와 직접 대조하되, 나머지 답의 정확성·권리·원문 오염은 별도다. 소형 gate에서 실제로 고쳤는지 확인한 뒤 16건 모집단과 학생에게 보낼 교정본 선정 규칙을 새 단계로 사전등록한다.

### Stage1fW — 교정형 full16 후보 생성, 검증/학생 학습과 분리

[후속 SH](../run_P106B_Stage1fW_teacher_repair_full16.sh)는 이번 세션에 **코드·CPU 계약만** 준비한다. 사용자 새 smoke PASS와 idle GPU, v1/v2/v3 정확 SHA가 선결이다. 원래 고정16 영어 쌍 모두를 교정형 Stage1dW와 같은 프롬프트·공식 thinking sampler·medium/ctx6144/max4096/사고예산2048로 재요청하고, `HF/sft_ready/p106b_teacher_sft/v4/teacher_repair_full16_candidates.jsonl`에 원문/교사 사고/최종답/교정 선언/사용량을 write-once로 저장한다. 원본 v1/v2/v3와 기존 학생/체크포인트는 수정하지 않는다. 최소 JSON완결12/16과 hard wall3300초는 **후보 생성의 형식 문턱**이다. 교사가 `CORRECTED`라 해도 자동 교육 수락은0; 실제 수치·코드·시점/정체성 주장과 출처/권리를 별도 검토해 명시 거부/불확실/채택 근거를 새 버전 manifest에 기록해야 한다. 이후에만 학생 micro8×accum16/ckpt-on의 교정형 별도 tag와 같은 노출량 대조를 열며, 현재 Stage1bW 옛 tag를 재사용하지 않는다.

### Stage1cW — 같은 부모와 SFT 자식의 고정 공개 벤치·오답 회수

[posthoc 비활성 템플릿](../scripts/templates/P106B_Stage1cW_parent_student_posthoc.sh.in)은 Stage1b의 checkpoint·데이터셋 SHA를 먼저 대조하고, 기존 P076 mean과 새 P106B 학생을 **같은 legacy tokenizer·형상·P100 고정9문항×두 프롬프트 형식**으로 생성하도록 설계했다. 원답36행을 [P100 답안 triage](../scripts/diag_p100_answer_triage.py)로 보수적으로 분류하고, KLUE YNAT·NLI·ARC Easy는 공개 자산에서 과제별 `n=512, seed=99`를 같은 두 모델로 재며 문항별 gold/pred/마진·건너뛴 사유를 각각 저장한다. [paired 오답 진단기](../scripts/diag_p106b_posthoc.py)는 정답률/오답률과 부모만 맞음·학생만 맞음·둘 다 오답을 분리하고 회귀한 문항 ID를 사람 검토로 보낸다. 사용자가 미래에 활성화된 SH를 실행하면 기존 벤치 계약대로 **W&B에도 요약이 전송**되지만, 로컬 문항별 원본이 정본이며 Codex는 전송을 실행하지 않는다. **각 과제512문항 표본과 P1009문항은 정식 전체 벤치가 아니고**, 두 모델 전후 차이는 추가 학습 효과이지 교사 방법의 인과효과 단독 증명이 아니다. 틀린 문항의 사실·한국어 뜻·형식·맥락·추론·반복·원천번역 오류는 저장 원답을 사람이 직접 분류한다.

### Stage2W — 한국어 품질·멀티턴 진단(조건부, 아직 런처 없음)

Stage1a/b에서 관찰한 실제 완성률·교사 출력토큰/벽시계와 저장된 `v1` 교사 원답을 보고 OASST2 한국어 번역을 더 넓힐지, 근거형 C자료를 섞을지 결정한다. **사람의 전수 사전승인을 학습 시작의 필수조건으로 두지 않는다.** 다만 그 출력을 검증형 `ACCEPT`라고 부르지 않고, 대표 32행 이상을 **학습 후** 문맥·번역 충실도·안전성 오류로 표본 감사해 `v2` 수정 우선순위를 만든다. 같은 P076 부모·legacy tokenizer·고정 질문·평가원천/학습 노출량의 `교사 pseudo-label` 대 `교사 없는 원천/독립 편집 답안`을 최소 2시드로 비교하고, 사용자 허용 범위의 2~4 epoch·유니크 행수·누적 assistant 토큰을 함께 기록한다. base full-val 망각, 한국어/영어 직접답·형식·다회전 원답안, 정답률·오답 유형을 별도로 본다. **이때만 지능·SFT 적합성 후보 판정**을 검토하며, 원천·평가 겹침/사용권이 미결이면 능력 승격은 보류한다. Stage2의 학습량·GPU 시간은 Stage1a 완성률과 고유 번역량 없이 아직 산정할 수 없어 본런 SH를 서둘러 만들지 않는다.

> **2026-09-27 경로 교정**: 위 Stage2W 문단의 `v1` 번역 확대와 `v2` 수정은 최초 A안의 역사 설계다. 실제 사용자 선택은 원답 교정 D안이며, 새 v4 **미검증 후보**의 근거·거부/불확실 상태를 검토한 다음 별도 선정본을 만들어야 한다. Stage1fW의 형식 PASS만으로 학생 SH를 열지 않는다. 이 단계의 2~4 epoch·동일 노출 no-teacher 대조와 한국어 멀티턴 원답안은 여전히 별도 사전등록·미실행이다.

### 대체 데이터 경로 B/C — 같은 분모로 섞지 않음

| 안 | 교사 역할 | 독립 근거와 실제 차이 | 현재 범위·대가 |
|---|---|---|---|
| A 역사 초기 권장 OASST2 영어→한국어 | 번역·표현 교사 | 사람 참여 원답을 보존하지만 원답 오류도 그대로 옮김(결과101 WebRTC) | **형식 gate에는 사용**, 현재 교육원천 권장안 아님. v1 번역9/16 미달·원답 사실 오류 |
| B 프로그램 정답형 QA | 한국어 문항/답변 표현 교사 | 정답은 solver가 계산해 오류 자동 거부, 내용 폭은 좁음 | 가장 안전한 배선 대조. 대화 지능 일반화 근거 없음 |
| C `concept`+국립국어원 뜻풀이 | 근거 문장에서 질문·답 형식과 쉬운 설명을 만드는 교사 | 목록 자체는 27파일·38,089줄의 **단어만**; CP949 ‘4만 어휘’ 40,000행 의미 열은 전부 채워지고 concept 고유37,810 중37,720 표제어 일치. 뜻풀이·동형어 번호가 근거이지만 용례 전용 열은 없음 | 사용자가 정확 경로 읽기만 승인. [한국어기초사전 저작권 정책](https://krdict.korean.go.kr/kor/openApi/openApiRegister)의 저작자표시·동일조건변경허락 적용 가능성을 파일 계보/산출물 사용 방식과 대조하기 전 학습 원천 미채택. 원문 수정/복사·SH 입력 자동 연결 금지 |
| **D 사용자 선택: OASST2 원답 교정 후 한국어 QA** | 교사는 원답을 무조건 번역하지 않고 오류 교정·불확실성 표시 | Stage1dW 3/3 JSON·WebRTC API 사실 복구. 그러나 GPT‑3 수치 새 오류로 자기수정은 verifier 아님 | 새 v4 full16 후보를 먼저 생성하고 원천/교정 근거를 점검한 **별도 선정본**만 후속 학생 실험에 사용. 전수 사람 사전승인은 기술 필수조건이 아니나 명백한 오답 자동 수락 금지 |

C 원천을 사용자가 승인한 **정확 두 파일만** 추가 실사했다. `/mnt/z/TinyDataset/참고용외부데이터/국립국어원/한국어기초사전/한국어기초 어휘(4만개).txt`는 CP949·40,000행/고유 표제어37,720·의미 nonempty40,000·동형어 최대10행이며 SHA-256 `463CF0D5204B31991D1004C2C553BA3AD2354D62CF7BF15B2DBE541E043F03FA`다. `한국어 학습용 어휘 목록.txt`는 CP949·5,965행/고유5,858, `풀이` nonempty4,009 중 한자 포함3,290·한글 포함487로 **뜻풀이 정본이라기보다 원어·표기 성격이 강하다**(SHA `3B49681F05D6A7490C13DA2A2847E433EFFDF65DA409FD295792D6EE33685064`). 두 자료 모두 별도 `용례` 열이 없고 현재 SH는 어느 보호 원본도 읽지 않는다. 공식 누리집의 이용조건이 이 로컬 추출본의 정확한 취득 경로·파생 dataset/모델에 어떻게 적용되는지는 별도 검토 대상이다.

기존 `ko-en`의 **단순 다음토큰 캐시**를 교사가 질문·답으로 변환하는 네 번째 후보도 가능하지만, 토큰 `.bin`의 임의 1024 경계를 그대로 질문으로 삼으면 문서 출처·완결 문맥·근거 답의 경계가 없다. P037에서 기존 300M/600M train–val 동일 EOS 문서 2/6건이 확인돼 문서 ID·공통 val 누출 정리가 먼저다([결과023 §12](../test_result/023_20260802100000_P037-단계2-필터는작동-검증이엉뚱한캐시를쟀다.md)). 사용하려면 승인된 공개 원문 문서에서 근거 범위를 고정하고, 교사가 질문과 답을 생성하되 원문 인용 위치·문서 계보·QA 오류를 별도로 보존해야 한다. 지금의 Stage1a/b는 이를 OASST2와 섞지 않는다. 기존 공개 v3 canonical 3,154행을 교사가 재표현하는 길도 있지만 한국어 비율5.83%·사람/오염 gate 미완을 해결하지 않으므로 P090B와 분리해 후속 비교한다.

## 5. 판정 기준·사전등록 범위

| 관측 | 판정 |
|---|---|
| Stage0 원본 SHA/선별 수16 미달·공개 v3 정확 질문 누출 | `HOLD8` 또는 입력결함 `FAIL9`, 교사 시작 금지 |
| Stage1a 구조화 완성 <12/16·wall>1800s·GPU 여유 미달 | **형식/자원 음성** `exit8`; 출력이 있어도 전부 미검증 후보 |
| Stage1b 교사 실시간 출력 고유 유효쌍<8/16·teacher/학생 OOM·표본 free<2GiB | 기능/자원 음성 `exit8`, 업데이트0 또는 부분 이력을 정확히 기록 |
| 형식/독립 loss 마스크 위반, 원본/부모/tokenizer SHA·태그 충돌, 프로세스/계측 오류 | 도구 실패 `exit9`, 품질 음성으로 오독 금지 |
| Stage1b 2업데이트·유한 gradient·assistant-only 지도토큰>0·교사 동시 생성 관측 | **기능 PASS만**. 번역 진실성·실무 학습속도·대화능력·정식 `TRAIN_READY`는 `NOT_RUN` |
| Stage1c 부모/학생 같은 P10036·공개 3과제×512의 문항별 원본·paired 추적 | **사후 진단 완료**. 회귀·개선 문항과 오답률만; 교사 단독효과·전체 지능은 `NOT_DECIDED` |

기존 P090B의 원천 manifest 세 필수 gate가 `PASS`가 아니어도 이 **분리된 미검증 연구용 2업데이트**를 정식 SFT로 표기하지 않고 수행할 수 있다. 이는 `train_sft_p090.py`의 formal fail-closed 규칙을 약화하는 것이 아니라 **다른 출력 네임스페이스·다른 목적의 실험**이다. 일반 SFT의 모든 답변을 독립 참으로 증명할 수 없으므로 Stage2의 실질 품질/모델 승격에는 고정 benchmark·오답 유형/번역오류 사후감사·동일 조건 대조가 필요하다.

## 6. 비용·자원

| 단계 | 예상 상한 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU, 공개 OASST2/v3/tokenizer 읽기 전용 |
| Stage1aW | 0.5h hard wall | 사용자 GPU full 교사 단독, ctx1024, ≤16×768 생성토큰+사고토큰 |
| Stage1aWb | <0.17h hard wall | 이번 지시 한정 Codex 직접 CPU+GPU ≤10분, 공개4쌍×cap2, 모델/학생 checkpoint 쓰기0 |
| Stage1dW | <0.16h hard wall | 이번 지시 한정 Codex 직접 CPU+GPU ≤10분, 오류2+solver대조1, 학생 학습/체크포인트0 |
| Stage1fW | ⚙0.5~0.9h, hard wall3300초 | 사용자 GPU 교사 단독, 고정16 교정 후보 생성·원본 보존, 학생 학습0 |
| Stage1bW | 약0.5~0.75h(첫 compile/교사 지연 변동, hard wall2700s) | 사용자 GPU full 교사+P076 학생, 최대2업데이트, 고유 진단 checkpoint 예상0.45GiB |
| Stage1cW | 약1.5h(공개 3과제×512와 P10036) | 사용자 GPU 모델2개 순차 평가, 보호 held-out0·문항별 원본 write-once |
| Stage2W | `NOT_ESTIMABLE` | 승인 원천의 실제 유니크 지도토큰·교사 accepted sample 비용·동일평가 확인 후 산정 |

## 7. 실행 파일·사전 점검

- Stage1aW: [run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh](../run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh) — 2026-09-27 사용자 실제 번역16건·완결9/16, 문턱12 미달 exit8. v1을 덮거나 동일 SH를 재실행하지 않는다.
- Stage1bW: [run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh](../run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh) — 상류 미달로 check-only 중단, 학생 학습0. 당시 종료9는 선결 음성을 도구 오류로 포장한 분류 결함이었고, 후속 CPU 재검사에서 HOLD8로 수정했다. 새 SH를 만들더라도 WSL smoke의 **수정 뒤 코드** 사용자 PASS를 선결로 한다.
- Stage1aWb/Wc: Wb는 기본 sandbox NVML 차단으로 적재 전 종료9([역사 SH](../run_P106B_Stage1aWb_teacher_budget_attribution-done.sh)); Wc는 허용된 한정 GPU 경로에서 4쌍·8요청 종료0([완료 SH](../run_P106B_Stage1aWc_teacher_budget_attribution-done.sh)). 원본 v1 덮어쓰기0, 학생 학습0.
- Stage1dW: [완료 SH](../run_P106B_Stage1dW_teacher_answer_repair-done.sh) 교사 수정형3/3 형식 통과이나 1개 답에 새 수치오류. 세 후보 모두 자동 학습수락0, 후속 별도 검증/개선 대상.
- Stage1fW: [사용자 실행용 SH](../run_P106B_Stage1fW_teacher_repair_full16.sh)와 [진단](../scripts/diag_p106b_teacher_answer_repair_full.py)의 self-test/check-only만 PASS. 새 smoke/모델 E2E는 `NOT_RUN`; §Stage1dW의3/3을 full16 성공률·정답률로 승격 금지.
- Stage1cW: [비활성 SH 템플릿](../scripts/templates/P106B_Stage1cW_parent_student_posthoc.sh.in)만 있다. Stage1b 고유 checkpoint가 아직 없어 루트 SH/TSV에 등록하면 입력태그 린터가 실제 FAIL한다. 사용자가 Stage1b 로그·체크포인트를 회신해 SHA/메타데이터를 판독한 **다음 지시**에서 새 단계명으로 활성화한다. 생성 답안·문항별 벤치 원본이 결과문서의 근거다.
- Stage2W: 원천 수·사람 표본·평가 설계 미확정이므로 **SH 미작성**. 두 준비 SH가 존재하는 것과 Stage2 본학습 사용 승인은 다르다.
- tag `p106b_s1b_oasst2_ko_online_s1337`: 레지스트리 조회에서 기존 로그 충돌0. 새 Stage1b 출력은 P106B 고유 이름이며 기존 P076/공개 SFT/교사 파일을 덮지 않는다. 과거 P076 mean은 같은 시작점 전후 진단의 부모이지 **동일 학습량의 교사 없는 대조군**이 아니다.

### exp-preflight — 이 계획의 알려진 실수 차단

| 축 | 판정 | 근거/미해결 |
|---|---|---|
| 독립변수 | PASS(기능 gate) | `교사 실시간 pseudo target 사용`이 Stage1b 목적; source16 반복·2업데이트만 |
| 계산/유효배치 | PASS | 8×16×1024=131,072 위치/업데이트, 2회 상한262,144. 실제 assistant target 토큰은 실행에서 따로 센다 |
| 풀≥2× | 예외·품질 판정 금지 | SFT는 의도적 epoch/중복 노출을 쓰며 이 기능 gate는 ≤16유니크·반복; pretrain 2× 풀 규칙을 학습효과 PASS로 복사하지 않음 |
| 태그/덮어쓰기 | PASS(정적) | 신규 tag 충돌0, 버전드 dataset·고유 진단 checkpoint write-once, 기존 checkpoint 수정0 |
| 동일 비교 | `PARTIAL_DESIGN` | Stage1c는 같은 부모/tokenizer/고정문항 전후 비교를 준비. Stage2 이전에는 no-teacher matched control이 없어 교사 품질 인과효과 판정 불가 |
| GPU/속도 | 제한 추산 | Stage0pW ctx512 full 교사+micro8/ckpt-on 표본 free4422MiB는 Stage1b ctx1024·실문장 peak 보증 아님; Stage1b 시작/공존 free 문턱으로 fail-closed |
| 수치·지능 판정 | `NOT_RUN` | Stage1c 문항별 오답 회수는 준비됐지만 2업데이트 결과로 일반 지능 향상 주장 금지; Stage2 대조 필요 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 8. 한계·보호선

OASST2의 review/rank는 사실성 보증이 아니다. 교사 번역도 독립 정답이 아니므로 P106의 검증형 `ACCEPT` 원장을 이 실험으로 채우지 않는다. 출처 카드 Apache-2.0 표기는 개별 텍스트의 개인정보·권리 승인이 아니다. 자동 연락처/숫자 검사는 **명백한 경우만** 걸러 의미 왜곡 전부를 검출하지 않는다. 그래서 원문·교사가 실제 가르친 문구·선정/거부 상태를 버전드 데이터셋에 남기고 사후 분석한다. 사전 파일의 뜻풀이가 전부 존재해도 다의어 표준번호·출처/라이선스·용례 부재를 건너뛰지 않는다. GPT가 보호 `concept`/사전 원본을 HF에 복사하거나 학습·GPU를 대신 실행하지 않는다. 성공해도 16유니크×2업데이트의 과적합·분산 때문에 Stage2 대조 없이 데이터 채택을 판정하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-27: 사용자 질문에 따라 ‘독립 정답 전수승인’이 일반 SFT의 필수조건이라는 과도한 전제를 철회하고, P106 검증형 `ACCEPT`와 P106B 자동 번역 `PSEUDO_UNVERIFIED`를 분리했다. 승인된 정확 `concept`와 사전 두 파일만 읽기 전용으로 구조·겹침을 확인했다. OASST2 Stage0 CPU 선별 자기시험/check-only에서 1326→잔존138·선정16을 확인했다. 교사 실제 번역·학생 학습·새 smoke는 `NOT_RUN`이다.
- 2026-09-27: 사용자 [결과101](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 새 smoke43/0/0/0 뒤 Stage1aW 교사16응답 중 완결9·미완결7, 실측 wall173.97초·총 생성10,429토큰을 회수했다. `12/16` 사전 문턱 미달은 §3이 경고한 형식 음성으로 유지한다. 당시 파서는 비정상 `finish_reason`을 하나로 뭉치고 사고/최종 부분출력·행별 사용량을 저장하지 않아 **절단 원인 귀속이 불가**하다. Stage1bW는 상류 실패 뒤 check-only에서 종료9로 잘못 분류했고 실제 교사+학생 학습은0회였다. 후속 코드는 같은 v1 문턱을 HOLD8로 고쳤지만 원본 로그는 수정하지 않는다. 새 설정의 재실행은 다른 단계·데이터 버전으로만 연다.
- 2026-09-27 후속: Stage1aWb는 기본 sandbox NVML 실패로 교사 적재0, Stage1aWc는 사용자 한정 허용 경로에서 4쌍 대응 cap768 0/4 대3072 3/4 완결을 확인했다. 사고문은 양쪽4/4 존재, 최종 문구는 큰 cap3/4에만 있었다. v2 raw는 불변이다. 직접 읽은 WebRTC 번역은 원문 API 오개념을 옮겼고, 교사 교정형 Stage1dW는 세 문항 JSON3/3을 냈으나 자기 `CORRECTED` 2건 중 하나가 GPT‑3 175B를 **175억**으로 새로 오기했다. [결과101 §9](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 외부 API/논문 근거 대조에 따라 그 행은 REJECT, WebRTC는 API 사실만 부분 확인, 수학50·20은 산술 확인이다. v3 원본·점검표를 별도 보존하고 자동 `ACCEPT`/학생학습0을 유지한다.
