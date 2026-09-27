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

역사 런처 `run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh`는 재현명령을 [결과101 §5 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존한 뒤 삭제했다. 이 런처는 Stage0W CPU 검사 뒤 Prism build10743·같은 SHA Bonsai 2 PTQ1_0을 **localhost 인증·offline·GPU full**로 기동했다. 16개 영어 사용자/사람 답을 한국어 질문·답 JSON으로 요구하고 v1 후보를 write-once 저장했다. 선택 문턱은 JSON≥12/16, wall≤1800초, GPU 시작/교사 적재 후 free≥8192/2048MiB였다. **실측 완결9/16·exit8**이었다([결과101 §1](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 모든 후보는 `UNKNOWN`/학습 target0이며 P106 검증형 `ACCEPT`가 아니다.

### Stage1bW — 사용자 시도 완료·선결 중단, 학습 NOT_RUN(결과101 §2)

역사 온라인 런처 `run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh`도 [결과101 §5 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 재현명령을 보존한 뒤 삭제했다. Stage1aW 원본/manifest SHA·완료 문턱을 선검사하고 학습 완료 P076 B3 mean checkpoint를 학생 시작점으로, legacy tokenizer·micro8×accum16/ckpt-on·Muon RMS4/AdamW를 쓰도록 설계했었다. 실제로는 상류 형식9/16 때문에 check-only에서 중단돼 학생 로딩·학습0이다.

학생을 먼저 올려 GPU 여유를 확인한 뒤 full 교사를 같은 GPU에서 ctx1024로 올린다. 교사에게 **실제로 다시 요청한** 한국어 문장 중 JSON/완료/기본 한국어·숫자·명백한 연락처 필터를 통과한 것만 별도 `PSEUDO_UNVERIFIED` 기록과 canonical assistant target으로 보낸다. 16개 중 유효 고유쌍 최소8개가 아니면 업데이트0·`exit8`. 유효쌍을 반복해 매 업데이트 `micro8×accum16=128`개 대화 노출, 총2업데이트로 제한한다. 이는 **최대 262,144 위치**(`2×8×16×1024`)의 처리 상한이지 assistant 지도토큰의 실측이 아니다. 원본 데이터/기존 checkpoint를 고치지 않고 새 runlog와 `HF/sft_ready/p106b_teacher_sft/v1/` 아래 **원문·교사출력 전체/자동 선정 canonical/각 SHA·조건 manifest를 write-once로 기록**한다. 모든 동시·loss 문턱을 지난 뒤 교사를 종료하고 고유 `runs/ckpt/m100R1c_ko-en_300M_p106b_s1b_oasst2_ko_online_s1337.pt` 진단 체크포인트 한 개만 저장한다(예상 약0.45GiB, 사용중인 기본 모델 덮어쓰기0). P100의 체크포인트·JSON 쌍 계약을 위해 같은 stem의 새 `runs/logs/*.json`도 기록하되 `final.val_loss=null`, 실제 assistant 지도토큰, `quality=NOT_RUN`으로 표시한다. 부모의 300M 예산을 이번 학습량으로 오인하지 않는다. `v1` 원본을 고치지 않고 문제행을 교정한 파생본은 `v2`로 만든다. 실제 지도토큰·유한 gradient/손실·동시 NVML/torch peak·교사 출력토큰/초·비용을 보고한다. 시작 다른 compute 앱0/free≥14GiB, 모델 공존 뒤 표본 free≥2GiB를 사전 중단선으로 둔다. `exit0`도 **기능 PASS**, 품질/`TRAIN_READY` 아님. LR `1e-4`/Muon 행렬 배수4/WD0은 SFT pilot 임시값이며 pretrain 최적 LR로 오인하지 않는다.

### Stage1aWb/Wc — 2026-09-27 절단 원인·사고/최종 분리의 짧은 대응 진단

Stage1aWb는 기본 sandbox NVML 차단으로 적재 전 종료9였고, 별도 Stage1aWc 역사 런처는 사용자 이번 지시 한정 **10분 이하 CPU+GPU**로 실제 완료됐다. 두 `-done.sh`는 [결과101 §6~§7·재현 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 명령/상태를 남긴 뒤 삭제했다. v1의 미완결3건+완결 대조1건을 같은 `ctx4096`, medium, fixed seed와 [공식 thinking 샘플러](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#generation-parameters)에서 cap768/3072로 대응 비교했다. **이번 팔끼리만 cap 차를 귀속**한다. v1과는 ctx/샘플러도 달라 소급 단일효과 주장은 금지한다. 8요청158.757초, cap768 완결0/4 대 cap3072 완결3/4이며 후자1건은 사고문만 남았다.

신규 `HF/sft_ready/p106b_teacher_sft/v2/`에는 네 영어 원문·`finish_reason`·행별 사용량/시간·`reasoning_content`·최종 `message.content`·파싱된 `user_ko`/`assistant_ko`를 서로 다른 필드에 write-once로 남겼다. 런로그에는 문구가 아니라 cap별 건수·길이·토큰만 남겼다. 학생으로 보낼 수 있는 필드는 **완결 최종 JSON의 `assistant_ko`뿐**이지만, 이 실행에서 실제 target 채택·학습은0이다. 사고과정·영어 사람답·불완전 fragment는 target이 아니다. 네 건은 옛 실패를 과표집하므로 **12/16 본 모집단 문턱을 통과시키지 않는다.** 사용자 선택에 따라 단순 번역 full16 대신 교정형 Stage1dW 소형 진단을 거쳐 Stage1fW 교정형 full16 후보를 준비했다. 비사고 모드와 프롬프트 축약은 기각돼 쓰지 않았다.

### Stage1dW — 교사 원답 교정 가능성과 계보 보존의 3문항 gate

Stage1aWc 짧은 대응 진단은 cap768 완결0/4·cap3072 완결3/4였지만, 완결된 WebRTC 문항에서 **원래 사람 답안의 API 오개념을 교사가 충실하게 번역**했다([결과101 §7~§8](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 사용자는 이 문제를 단순 번역이 아닌 **교사 교정안**으로 후속 시도하고, 나중에 사람이 다시 검증·개선할 수 있도록 원문과 교정본을 보존하기로 선택했다. 이는 번역형 Stage1a와 **다른 교사 작업**이며 지능 품질 증거를 합산하지 않는다.

[독립 진단](../scripts/diag_p106b_teacher_answer_repair.py)의 Stage1dW 역사 런처도 [결과101 §9·재현 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존 뒤 삭제했다. v1/v2 정확 SHA를 확인하고 WebRTC 오개념, 시점·모델 자기소개, 산술 대조 세 문항을 사용했다. 교사에게 영어 원답을 **검증되지 않은 DATA**로 주고 오류를 고치거나 불확실성을 답하라고 요청했다. `user_ko`,`assistant_ko`,`correction_status`,`correction_note` 완결 JSON을 `medium` + 공식 thinking sampler, ctx6144/max4096/사고예산2048로 받았다. 자기 `correction_status`는 독립 진실 판정이 아니다.

`HF/sft_ready/p106b_teacher_sft/v3/`에 영어 질문/사람 원답, v1/v2 SHA, 실제 교사 사고·최종 원문, 파싱된 새 문답·교정 설명·종료/사용량을 write-once로 남긴다. **학생 학습·target 채택은0**이며 적어도2/3 JSON 완결은 형식 가능성 문턱일 뿐 내용 정답 판정이 아니다. WebRTC의 입력은 `constraints`, 반환은 `Promise<MediaStream>`이라는 [공개 API 근거](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)와 직접 대조하되, 나머지 답의 정확성·권리·원문 오염은 별도다. 소형 gate에서 실제로 고쳤는지 확인한 뒤 16건 모집단과 학생에게 보낼 교정본 선정 규칙을 새 단계로 사전등록한다.

### Stage1fW — 교정형 full16 후보 생성, 검증/학생 학습과 분리

[당시 Stage1fW SH의 재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 처음에 **코드·CPU 계약만** 준비됐고, 이후 사용자가 실행했다. 사용자 새 smoke PASS와 idle GPU, v1/v2/v3 정확 SHA가 선결이었다. 원래 고정16 영어 쌍 모두를 교정형 Stage1dW와 같은 프롬프트·공식 thinking sampler·medium/ctx6144/max4096/사고예산2048로 재요청하고, `HF/sft_ready/p106b_teacher_sft/v4/teacher_repair_full16_candidates.jsonl`에 원문/교사 사고/최종답/교정 선언/사용량을 write-once로 저장했다. 원본 v1/v2/v3와 기존 학생/체크포인트는 수정하지 않는다. 최소 JSON완결12/16과 hard wall3300초는 **후보 생성의 형식 문턱**이다. 교사가 `CORRECTED`라 해도 자동 교육 수락은0; 실제 수치·코드·시점/정체성 주장과 출처/권리를 별도 검토해 명시 거부/불확실/채택 근거를 새 버전 manifest에 기록해야 한다. 이후에만 학생 micro8×accum16/ckpt-on의 교정형 별도 tag와 같은 노출량 대조를 열며, 현재 Stage1bW 옛 tag를 재사용하지 않는다.

2026-09-28 [결과101 §10](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 사용자 Stage1fW 실제 생성 16/16 `stop+JSON`·278.659초로 **형식 문턱 PASS**를 기록했다. 하지만 직접 원문/답을 읽은 [행별 감사](../test_result/evidence/P106B_Stage1fW_candidate_review.json)는 명백한 교사 새 결함8, 추가 검토4, 잠정4다. 따라서 '형식이 되면 교육 후보는 품질이 충분할 것'이라는 낙관적 예측은 **기각**되고 교육 target 채택/학생 업데이트는0이다. 원본 v4 불변, 실행 SH는 재현명령과 Git 복구 이력 보존 후 `-done` 이력으로 관리한다.

### Stage1gW — 교사 프롬프트 강화·응답별 결함 훅과 제한 재요청 (사용자 승인 A)

독립변수는 **같은 v4의 명백한 결함8건에만 적용한 엄격한 원천 불변 프롬프트+결함 피드백 재시도**다. [진단기](../scripts/diag_p106b_teacher_targeted_repair.py)와 [완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 정확한 v1~v4 SHA 및 [16행 감사](../test_result/evidence/P106B_Stage1fW_candidate_review.json)의 원천 ID를 대조한다. 시스템 프롬프트는 원답을 불신 자료로 유지하되 지명·인물 성별·질문/답변 역할·숫자/단위를 임의 변경하지 말고, 표기가 불확실한 고유명사는 원문 Latin을 보존하라고 요구한다. 응답 직후의 **진단기 내부 validator**가 불완결 JSON, 예상 밖 아랍/키릴/한자 문자, 이번8행의 명시 지명·성별·어휘·역할 결함을 검사한다. 동일 결함이면 오류 코드만 교사에게 피드백하고 각 행 **최대3회**까지 다른 seed로 다시 생성한다. 전역 Codex 훅 설치가 아니라 이 실험에서만 쓰는 bounded response hook이다.

v5 `HF/sft_ready/p106b_teacher_sft/v5/targeted_repair_attempts.jsonl`에는 실패 응답을 포함한 **모든 시도**의 원문·사고·최종답·검사오류·사용량과 행별 첫 lint 통과 선택을 write-once로 보존한다. 사전 문턱은 8행 모두 3회 이내 **명시 결함 lint** 통과, hard wall≤1800초다. 통과여도 정답·번역 충실도·PII·권리·학생 교육 채택은 자동 승인하지 않고 `accepted_for_training=false`다. 모르는 오류는 놓치고 정상인 특수표기를 거부할 수 있으므로 사람/별도 GPT가 v5 후보를 v4 원문과 다시 읽고 다음 선정 버전을 결정한다. 형식16/16인 v4와 선별 결함8인 v5의 통과율은 모집단·프롬프트·retry가 달라 인과 비교 불가다. 기존 학생 Stage1b를 재실행하지 않는다.

preflight: 학습 step0·draw0·새 checkpoint/tag0이므로 pretrain의 풀≥2× 규칙과 micro/accum은 적용 대상이 아니다. 동일 원본/교사 SHA·v4 파생 원천을 고정하고 새 v5 출력만 허용한다. 기존 Stage1d/f와는 답안 과제·선별·프롬프트·retry가 함께 달라 품질 우열을 주장하지 않는다. 예상 GPU full 교사 ≤0.5h, 경쟁 프로세스0·시작 free≥8192MiB·교사 적재 뒤 free≥2048MiB에서만 계속한다. `--self-test`·`--check-only`는 모델 비실행이고 8개 과거 결함이 정확히 validator에 걸리는지를 확인한다. **이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.**

2026-09-28 사용자 [결과101 §11](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 실제8행/13요청·교사 completion28,677토큰·474.232초, 명시 결함 lint7/8<사전8/8로 유효한 음성 `exit8`이다. 행11은 세 번 모두 미완결 또는 이름의 키릴/아랍 문자 혼입으로 fail-closed했다. 그러나 [v5 직접 점검](../test_result/evidence/P106B_Stage1gW_candidate_review.json)은 lint 통과7행 안에도 인명 훼손·혼합어·태양 거리의 10~100배 축소·역할 문장의 어색함을 발견해 명백 오류 총5, 추가검토2, 잠정1로 기록했다. **예측했던 ‘명시 결함 재시도만으로 8행을 교육 후보로 정리’는 기각**하고 자동 학습 채택0을 유지한다. 원본 v5 모든 시도는 불변, 같은 Stage1gW 재실행은 금지한다. 후속은 교사에게 canonical/ChatML 형식을 맡기지 않는 파서·래퍼 분리와 새 데이터 버전/단계에서만 연다.

### Stage2aW — 300M~600M 학습/자료 토큰 분모·교사 비용 선결 (CPU)

[읽기 전용 계산기](../scripts/diag_p106b_scale_preflight.py)와 [사용자용 SH](../run_P106B_Stage2aW_sft_scale_preflight.sh)는 정확 v4 SHA와 legacy 학생 tokenizer SHA를 확인하고 16개 한국어 대화를 기존 canonical→ChatML 인코더로 센다. v4 실측은 **학생 전체 직렬화 2,040토큰·assistant 지도 1,298토큰**을 만드는 데 교사 completion(사고+최종) **17,698토큰·278.659초**였다. 300M/600M이 (a) 학생 모델 처리 위치, (b) 고유 직렬화 데이터, (c) assistant 지도 토큰 중 무엇인지 분리한다. 1~4epoch을 구별하며 `8×16×1024=131,072`은 **고정 길이 패딩을 포함할 때의 명목 위치/step**일 뿐, 현재 가변 길이 SFT 배치의 실제 비패딩/지도 토큰 수가 아니다.

같은 작은 v4 생성 속도와 평균 길이를 기계적으로 연장하면 고유 직렬화300M에 교사 약474일, 4epoch 하한인 고유75M에도 약119일이라는 **규모 경고**가 나온다. 그러나 샘플이 결함 포함 한국어16·교정형 사고 출력이고 배치/포맷·영어/거부율이 바뀌므로 이것은 예산 확정이나 처리량 예측이 아니다. 고유자료·노출량·문항 중복/라이선스·교사 사고/최종 생성량을 서로 다른 열로 보고한다. `--self-test`/`--check-only`는 CPU에서 PASS, 실제 대량 교사/학생 모델·영어 생산성은 `NOT_RUN`이다. 토큰 분모 사용자 결정 전 300M/600M 본훈련 조건이나 새로운 tag를 확정하지 않는다.

### Stage2bW — 교사 내용과 학생 양식의 소유권 분리 (CPU)

[순수 래퍼](../scripts/p106b_teacher_wrapper.py)와 [계약 SH](../run_P106B_Stage2bW_content_wrapper_contract.sh)는 교사 출력에서 얻은 **질문/답변 텍스트**만 받아 역할 순서·출처 ID/SHA·언어·교사 SHA·미검증 라벨을 코드가 부여한다. `tinylm.chat.canonical.normalize/validate`가 버전드 대화 JSON을 만들고, 기존 `tinylm.chat.serialize`와 `tinylm.data.sft.encode_conversation`가 토크나이저별 ChatML 문자열·assistant-only 마스크를 만든다. 교사 사고, JSON 문법, ChatML 경계/role token, 지도 마스크는 교사에 맡기지 않는다. 멀티턴도 코드가 `user→assistant` 쌍을 최대4회 조립하고 잘못된 경계 토큰·제어문자는 거부한다. 현재 합성 두 턴·마스크 CPU fixture PASS, 실제 교사 v5/대량 원천→새 canonical 자료는 `NOT_RUN`이다.

이 래퍼는 교사가 어떤 **전송 문법**으로 질문/답을 보낼지를 아직 결정하지 않는다. ① 태그 필드 뒤 파싱, ② 제한형 JSON, ③ source 질문 유지·답변만 생성의 세 경로를 사용자 질문 기능으로 비교했으며 선택 전에는 구 형식 Stage1gW를 소급 변경하지 않는다. 전송 문법 확정 뒤 새 Stage2cW 교사 소형 bilingual·주제별 패널을 별도 버전에서 만들고 실제 parse/중복·한영 5:5 토큰 계측을 통과해야 300M 학습 SH를 READY로 승격할 수 있다.

**사용자 선택 2026-09-28:** 교사는 태그 필드로 질문·답·간단 메모의 내용만 쓰는 A안으로 정했다. teacher thinking은 버리지 않고 별도 원본 sidecar에 SHA와 생성 ID로 보존하되 현재 canonical에는 **sidecar 참조/해시만** 쓴다. 현 `tinylm.chat.serialize.loss_spans()`의 기본 `train_thinking=True`와 미완 `train_thinking=False` 구현 상태에서 사고문을 canonical의 활성 `thinking` 블록에 넣으면 의도치 않은 지도 토큰이 되기 때문이다. 장래 reasoning 학습은 별도 데이터셋 버전과 loss-mask/권리/품질 계약을 통과한 뒤 판단한다.

### Stage2cW — 동일 교사 16문항의 태그 대 JSON 출력형식 비용 대응 게이트

[국소 format adapter](../scripts/p106b_teacher_format.py)는 `qa_generate`, `translate`, `repair`, `diversify`, `next_turn`의 작업 종류를 코드가 지정하고, 교사는 `[[QUESTION]]`, `[[ANSWER]]`, 선택 `[[NOTE]]` 본문만 작성한다. 역할·토크나이저·ChatML과 독립 verifier는 모델에 맡기지 않는다. 교사 자기 교정 설명은 참고 메모이지 참 판정이 아니다. [Stage2cW 진단](../scripts/diag_p106b_teacher_tagged_pair.py)과 [사용자 SH](../run_P106B_Stage2cW_tagged_json_pair.sh)는 기존 v4와 같은 고정16 영어 OASST2 원문을 출처로, 동일 모델·중간 사고·sampler·ctx·출력상한·seed에서 **태그 vs JSON 대조**를 팔 순서 ABBA로 32회 수행한다. 두 팔의 의미지시는 같고 출력 문법만 바꾸며 행별 completion token(사고 포함)·최종 글자·요청 wall·파싱 완결·canonical 래퍼 성공을 새 v6에 write-once 저장한다.

사전 문턱은 tagged `stop+필드+canonical` ≥12/16, hard wall≤2400초다. 더 짧거나 빠르다는 주장은 양 팔의 개별 토큰/시간·순서 편향을 직접 비교한 뒤에만 한다. 이 16개는 한국어 변환 과제라 **한영 5:5 생산성이나 300M 처리량을 증명하지 않는다**. 실제 교사 GPU는 사용자 실행 전 `NOT_RUN`; CPU self-test/check-only만 PASS다. 새 답 역시 교육채택0·독립 정답성 `NOT_RUN`으로 보존한다.

### Stage2dW — v6 태그 후보를 독립 canonical/ChatML 파일로 래핑하는 작은 교량

[materializer](../scripts/build_p106b_tagged_pilot.py)와 [사용자 SH](../run_P106B_Stage2dW_tagged_pilot_canonical.sh)는 v6의 tagged 완결≥12/16과 미리 고정한 val cases2·15를 선결로 요구한다. 교사 raw의 사고/최종을 고치지 않고 [코드 소유 래퍼](../scripts/p106b_teacher_wrapper.py)로 질문·답만 canonical `user→assistant`에 넣고 출처·라이선스 카드 상태·모델/원천 SHA·`PSEUDO_UNVERIFIED`를 부여한다. `teacher_reasoning_content`는 원본 v6에만 남기고 canonical meta에는 원본 sidecar SHA/행 참조를 둔다. 기존 legacy tokenizer로 길이≤1024·assistant 지도 토큰>0과 train/val 첫 질문 해시 불겹침을 확인한다. [write-once sharder](../scripts/p106b_shards.py)는 UTF-8 행을 자르지 않고 각 JSONL 파일 **20,000,000 byte 이하**로 분할하며 shard별 SHA·전체 이어붙이기 SHA를 manifest에 기록한다. Git에 자동 staging/push하지 않는다.

현재 v6가 없으므로 Stage2dW `--check-only`의 `HOLD8`은 정상 선결이다. v7 작은 한국어 자료가 생겨도 **300M/600M 학습자료는 아니다**. 이후 대량 자료는 원천 concept ID·주제 가족·언어별 목표와 유니크/근사중복률을 먼저 고정하고, 주제·형식·지식·논리·일상·문화·사회·수학/코드·게임/TRPG/밈을 별도 계수해야 한다. 독립 대화는 매 요청 새 메시지로 시작하고, 멀티턴에서만 같은 대화의 앞 턴을 의도적으로 전달한다. seed 변경만으로 같은 concept를 무한 반복하지 않으며 concept당 변형 상한과 novelty 하한에서 생성 부족을 그대로 `HOLD`한다. 한영 5:5는 행 수가 아니라 학생 토크나이저의 **비패딩 학습 처리 토큰**으로 측정하고 assistant 지도 토큰/교사 사고+최종 토큰은 별도 열로 보고한다.

### Stage2eW — 현재 로컬 공개 원천의 유한 교사 작업표

[작업표 builder](../scripts/build_p106b_job_deck.py)와 [완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 기존 공개 v3 train/val의 정확 SHA를 **읽기만** 확인한 뒤 새 무시된 HF 버전에 20MB 이하 job JSONL shard를 write-once로 만든다. 한 단일턴 source concept에는 ko/en 각 최대1개(`repair` 또는 `translate`), 영어 멀티턴은 **기존 영어 맥락을 의도적으로 넣는 `next_turn` 1개**만 부여한다. 기존 멀티턴 전체를 번역하지 않고 한국어 답 한 줄만 섞는 무효 대화는 만들지 않는다. 분할은 source의 원 train/val을 generation 전에 유지한다. 매 job은 source ID/revision/card license, topic heuristic, concept ID, 목표 언어/작업 및 고정 seed 키를 갖고, 같은 concept를 목표 토큰 도달까지 다시 만드는 루프가 없다.

실제 로컬 v3의 CPU check-only는 train 한국어175행/34,946 직렬화토큰·영어2,821행/822,733토큰에서 유한 job **5,429건**(train en2,996/ko2,162; val en158/ko113)을 계산했다. 주제 heuristic은 general/other **4,589건**으로 편중되어 정치사회·게임/TRPG·수학·일상 등 요청 범위의 의미 품질/충분한 양을 증명하지 못한다. 5,429행과 이미 존재하는 857,679토큰은 75M 이상의 고유 학습 풀 자체가 아니다. `--execute`는 Codex가 실행하지 않았고, 새 job deck은 사용자 실행 전 `NOT_RUN`이다.

### Stage2fW — 8주제×한영×2고유 source의 32건 교사 생성 pilot

[32-job 진단기](../scripts/diag_p106b_bilingual_pilot.py)와 [사용자 SH](../run_P106B_Stage2fW_bilingual_teacher_pilot.sh)는 Stage2e job deck과 Stage2c 태그 필드/래퍼≥12/16을 선결로 둔다. 각 주제 heuristic×목표언어 조합에서 해시순 **서로 다른 source ID 2개**만 고른다(32개 고정). 교사는 `repair`, `translate`, `next_turn`을 job이 정한 대로 수행하고, 나중 확장에는 `qa_generate`, `diversify`를 별도 근거형 작업으로 사용할 수 있다. 독립 job은 매 HTTP 요청에 새 system+source만 보내며 서버 `--cache-ram 0`을 유지하고, 하나의 멀티턴 source에서만 앞 턴을 입력으로 포함한다. 단순 seed 변경을 새로운 concept로 세지 않는다. 태그 파싱 실패만 1회 재요청하고, 같은/근접 질문은 재요청으로 quota를 채우지 않고 거부한다.

원본 요청/사고/최종/거부 이유·교사 completion token/요청 wall은 새 무시된 HF 원본20MB 이하 shard에 전수 기록한다. 별도 기존 serializer로 각 선택 답의 student canonical 전체·assistant 지도 토큰을 한영별로 재어 **행수 16:16이 실제 토큰 5:5인지** 확인한다. 완료 기준은 ko/en 각 최소12개의 형식·길이·근접중복 screen 후보와 새 원본 SHA; 이것은 **정답·권리·PII·주제 의미 승인이나 300M 학습 readiness가 아니다**. `--self-test`만 CPU PASS, `--check-only`는 사용자 Stage2c/e 미수행으로 `HOLD8`, 교사·학생 모델은 `NOT_RUN`이다. Stage2c 태그 대 JSON의 completion token/벽시계 대비 이번 생성의 accepted candidate당 비용을 비교하되, 과제·소스가 달라 인과 속도 개선으로 합산하지 않는다.

### Stage2gW — 최종답만 학생에게 전달하는 2-update 소형 기능 게이트

[사용자 실행 SH](../run_P106B_Stage2gW_tagged_student_wiring.sh)와 [학생 코드](../scripts/train_p106b_tagged_pilot.py)는 Stage2d의 v7 canonical train/val 및 기존 P076 B3 mean legacy32 부모·tokenizer SHA를 선검사한다. 교사는 GPU에서 내린 뒤 학생만 올린다. 모델은 compile/default·grad checkpoint on, micro8×accum16으로 **2 업데이트**만 수행하고 assistant-only CE와 유한 gradient/실제 비패딩 처리 토큰·지도토큰을 별도 기록한다. 교사 사고는 canonical meta의 sidecar 참조라 loss target이 아니다. 기존 부모/원본/옛 Stage1b 태그는 고치지 않고 새 고유 `p106b_s2g_tagged_pilot_s1337` checkpoint/JSON만 write-once로 저장한다. 이는 온라인 동시 교사 Stage1b와 **다른 경로**이고, 예산300M·한국어/영어50:50·멀티턴 품질·base full-val/벤치/forgetting은 모두 `NOT_RUN`이다.

실제 v7 사용자 원본이 없으므로 `--check-only`는 올바르게 `HOLD8`이고 Codex는 모델을 실행하지 않았다. CPU `--self-test`에서 canonical 최종답만 mask되는 계약은 PASS다. 독립 원본 QA의 실질 성능과 교사 방법론의 인과효과는 고정 원문/부모·같은 노출량 no-teacher 대조 및 문항별 결과가 있어야 판정한다. 한정 기능 게이트 PASS 전 대규모 trainer를 READY로 만들지 않는다.

### Stage2hW — 사용자 이번 지시 한정 CPU+GPU 교사 effort 속도·완결률 실측

사용자는 온라인 교사를 5 optimizer update만 먼저 검토하도록 하고 이번 지시에 한해 CPU+GPU 직접 시험을 승인했다. `micro8×accum16`의 5 update를 매 microbatch 신규 자료로 수행하면 최대 **640개 교사 답안**이 필요하므로, 먼저 [독립 진단기](../scripts/diag_p106b_effort_profile.py)·[완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 **4문항×`none/low/medium`=12요청**으로 교사 비용을 실측한다. 모델/원천/태그 프롬프트/샘플러/ctx6144/max2048/문항별 seed를 고정하고 요청 순서만 교차한다. 서버는 `--reasoning auto`, `reasoning_effort`는 요청별 top-level 필드다. 사고예산 숫자를 별도로 넣지 않아 `none/low/medium`을 임의 0/512/2048 토큰과 동치라고 가정하지 않는다. 원본 v9에 사고·최종·finish·usage·벽시계를 write-once로 저장하고 runlog에는 집계만 찍는다.

[PrismML 공식 known issues](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/KNOWN_ISSUES.md)는 현재 template의 `none/low/medium`과 `none`일 때 서버 `--reasoning auto` 조건을 설명한다. 반면 [공식 demo README](https://github.com/PrismML-Eng/Bonsai-demo)는 `low`가 기대보다 길 수 있다고 경고하므로 **실제 local build에서의 종료사유/사고 길이를 직접 판독**해야 한다. 세 모드의 온전한 Q/A 생산량과 완결률을 보지 않고 빠르다는 이유만으로 대량 교사 기본값을 바꾸지 않는다. 이 단계는 교사-only 비용/형식이고 학생 5 update나 300M 품질 증거가 아니다.

Stage2hW 결과의 `completion_tokens`는 사고+최종을 합치며 요청 wall에는 HTTP/첫 호출 시간이 있다. 이후 학생 실제 1 update와 별도로 결합해 온라인 새 답안640개의 비용을 상·하한으로 추산한다. 추산이 큰 경우 5 update를 무작정 시작하지 않고 사용자에게 범위 재확인을 받는다. 이번 승인 전용 GPU 시험을 후속 세션의 영구 권한으로 승계하지 않는다.

2026-09-28 **이번 지시 한정 교사 단독 실측**: 고정4문항의 `none`은 4/4 완결·완료토큰1,063·요청벽시계18.568초, `low`는 4/4·5,166·83.406초, `medium`은 2/4·7,531·121.882초였다. `medium` 두 문항은 max2048에서 사고가 답변 예산을 소모해 `length`로 끝났다. 이 값은 **같은 4문항의 교사 요청 시간**이지 학생 5업데이트 처리율이나 300M 생산비용이 아니다. 이 Stage2hW의 세 팔은 원인 분리를 위해 모두 *thinking sampler*를 사용했으므로 특히 `none`은 모델카드의 비사고 권장 sampler가 아니며, 아래 Stage2iWb의 예상시간으로 그대로 옮기지 않는다. 새 원본 v9는 불변이다.

### Stage2iWa/Wb/Wc — 교사+학생 온라인 5 optimizer 업데이트 처리율 (사용자 실행 세 팔)

사용자는 120 optimizer 업데이트를 즉시 돌리지 않고 **5회만 먼저 실측**한 뒤 결과로 다시 결정했다. 이후 직접 실행은 하지 말고 아래 세 조건을 각각 SH로 준비하라고 지시했다. [공통 진단](../scripts/diag_p106b_online_rate5.py)은 Stage2e의 공개 v3 **OASST2 단일턴·영어 원천** 중 길이 상한을 통과한 365개 concept의 영/한 쌍을 고정 순서로 읽는다. ko는 번역, en은 원답 교정이다. 다섯 optimizer 업데이트 각각 micro8×accum16을 채우려면 **새 교사 출력이 수락된 640 대화**가 필요하다. 한 microbatch마다 새 출력8개를 요청하고 언어를 교대로 바꾼다. 같은 원천 concept의 영/한 출력은 쌍을 이루므로 **640개 독립 concept는 아니다**. 실패 출력은 새 source로 대체하되 언어당 고유 후보365개를 소진하면 `exit8`이며, 실패를 반복 seed로 감추지 않는다.

| 구분 | SH | 교사 사고/출력 예산 | 모델카드 sampler | 상한 |
|---|---|---|---|---:|
| A·Stage2iWa | [low](../run_P106B_Stage2iWa_online5_low.sh) | `low`, ctx3072/max2048 | thinking: temperature1, top_p.95, top_k20, min_p.05, presence0, repeat1 | 4h |
| B·Stage2iWb | [none](../run_P106B_Stage2iWb_online5_none.sh) | `none`, ctx1536/max1024 | instruct: temperature.7, top_p.80, top_k20, min_p0, presence1.5, repeat1 | 1.5h |
| C·Stage2iWc | [medium](../run_P106B_Stage2iWc_online5_medium.sh) | `medium`, ctx6144/max4096 | thinking: A와 동일, Stage2h max2048 절단 때문에 출력 예산 확대 | 6h |

[PrismML 공식 모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)는 thinking과 non-thinking sampler를 위처럼 다르게 권장한다. **현재 카드에는 `low`를 지원하지 않으며 xhigh에 가깝다고 적혀 있는데** 로컬 Stage2hW의 `low`는 4/4 완결·medium보다 짧았다. 카드/실물 런타임 차이 가능성이 있어 A를 정식 저비용 reasoning 경로로 가정하지 않는다. `--reasoning auto`와 요청별 top-level `reasoning_effort`를 유지하고 출력에서 사고·최종을 따로 기록한다. 사고 텍스트는 원본 `HF/sft_ready/p106b_teacher_sft/v10_online_rate5_<effort>/raw_*.jsonl`의 sidecar일 뿐 assistant 지도 target이 아니다. 소프트웨어가 교사의 `[[QUESTION]]`/`[[ANSWER]]`/`[[NOTE]]`를 파싱해 canonical 역할·ChatML·assistant-only 마스크를 소유한다.

세 팔은 동일한 P076 B3 mean 부모·legacy32 tokenizer·학생 micro8/accum16/ckpt-on, 모델 compile/default, Muon RMS4+AdamW를 쓴다. 동일한 공개 source/문항 순서를 쓰지만 교사 sampler/사고강도뿐 아니라 ctx/max 출력 상한도 달라 **팔 간 품질 또는 속도 차를 effort 단독 효과로 귀속하지 않는다**. 각 응답의 완료토큰·요청벽시계·format/reject, 학생 업데이트의 teacher/compute/전체벽시계·실제 비패딩 처리/assistant 지도토큰·언어별 토큰·전역 표본 peak와 PyTorch reserved를 별도 기록한다. 모든 시도와 학생 target은 20,000,000바이트 이하 write-once JSONL 샤드/해시 manifest로 남긴다. 시작 다른 GPU compute 앱0/free≥14GiB, 공존 후 free≥2GiB, 중간 free<512MiB·시간 초과·소스 고갈·형식 실패는 부분 이력을 보존하고 `exit8`이다. **체크포인트 저장0·held-out 평가0·정식 `TRAIN_READY`/품질 PASS0**. `exit0`은 이 제한 처리율 gate의 5업데이트 기능 완료일 뿐이다. 5회 결과와 한국어/영어의 실제 비패딩 토큰 비율·교사/학생 속도를 본 뒤에만 120회 온라인 지속 여부, chunk 선제생성/10GB 이하 RAM 버퍼의 필요성을 새 계획으로 결정한다. 이 세 SH를 큐에서 모두 연속 실행할 필요는 없다.

### Stage3W/Stage4W — 300M 먼저, 한국어 평가 통과 때만 600M (조건부)

사용자 정의 300M~600M은 **학생이 학습 중 실제 처리한 비패딩 직렬화 대화 토큰**이다. 이는 300M 고유 행이나 assistant 지도 토큰이 아니다. `micro8×accum16×seq1024`의 `2289/4578`은 패딩이 매번 seq1024까지 채워진다는 가정에서의 명목 step이며 실제 가변 길이 SFT 토큰 수를 보증하지 않는다. 향후 trainer는 처리/지도/패딩 위치/언어/고유 concept·epoch-equivalent를 런타임에 따로 세고 비패딩 목표에 도달하면 중단해야 한다. 2~4epoch 범위와 과적합 방지를 위해 300M에는 적어도75M, 600M에는 적어도150M의 고유 직렬화 토큰을 최저 문턱으로 두며, 같은/유사 concept를 seed만 바꿔 복제해 이 문턱을 채우지 않는다. 현재 고정16은 고유2,040토큰·명백 오류8이라 턱 밖이다.

1차 소형 장면 패널에서 포맷 완결·답안 문맥/사실 결함·한영 토큰율·중복·accepted row당 교사 output token/시간을 관찰하고, 다음 bounded shard에서 처리량이 유지될 때만 30M→100M→300M 학생 단계로 확장한다. 600M은 300M의 한국어/영어 직접답·형식·단기기억·논리·forgetting/오답 유형을 본 뒤 별도 조건부 승인이다. 교사 원천은 독립 지식 검증형 P106 `ACCEPT`가 아니라 `PSEUDO_UNVERIFIED` pilot이며, 사용자의 요청대로 오류 자체를 사전 전수 정답화하지 않아도 되지만 명백한 형식/PII/원천 누설과 반복복제는 기록·거부한다. 같은 부모와 같은 노출량의 교사 없는 대조가 없으면 교사 기여를 단독 인과효과로 주장하지 않는다.

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

사용자가 추가로 지목한 **정확 `한국어기초사전_json_20260819/` 폴더**도 2026-09-28 읽기 전용으로 실사했다. 11개 정규 JSON·약969MiB, 내부 `LexicalResource`/`Lexicon` 구조의 LexicalEntry **56,555레코드/고유 `val` ID53,671개**, Sense76,833개 모두 `definition` 보유, SenseExample594,578개 중 텍스트594,294개였다. 영어 Equivalent75,145개를 포함한 11개 언어 Equivalent 총826,505개이며 `homonym_number`·품사·어휘등급·의미 범주도 있다. 따라서 **뜻풀이·용례·영어 대역이 없어 word 목록만으로는 못 하던 근거형 한영 QA 후보**를 기술적으로 만들 수 있다. 그러나 ID 중복2,884건은 전부 같은 파일 안에서 발생하고 표본은 같은 target ID에 관용구 레코드가 붙은 경우였다. ID만으로 중복 제거하면 관용구·속담을 지울 수 있으므로 `target ID+lexicalUnit+Sense+원문 해시` 계보가 필요하다. 용례의 `대화` 유형63,436개는 중앙 길이23자이고 확인한 발화자 표지형 쌍은0건이므로 **멀티턴 user/assistant 정답 자료로 즉시 래핑할 수 없다**. 용례의 `type=1` 343건과 텍스트 빈 예284건도 parser 검증 대상이다.

JSON 내부에는 `한국어기초사전 - 국립국어원 제공`, 생성시각 `2026/08/19 12:38:21`은 있지만 이 11파일 안에 별도 LICENSE/다운로드 receipt는 보이지 않았다. [공식 전체 내려받기](https://krdict.korean.go.kr/download/downloadPopup)는 JSON 제공을 확인하고, [공식 저작권 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)은 별도 표기 없는 텍스트에 CC BY-SA 2.0 대한민국의 저작자표시·동일조건변경허락을 명시한다. 이는 **이 로컬 8월판의 정확 취득·예외 여부와 파생 SFT/모델의 배포 의무를 자동 확정하지 않는다**. 지금은 열거·구조/계수만 했고 JSON 문장·뜻풀이를 HF로 복사하거나 교사에게 전달하지 않았다. 사용자/권리 확인 뒤 별도 source manifest·출처표시·split/중복/PII·의미/용례 parser 검사를 통과한 **새 버전**에서만 활용한다. 기존 Stage2iWa/b/c의 OASST2 공개 원천과 혼합하지 않아 온라인 처리율 비교축을 보존한다.

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
| Stage1gW | ⚙≤0.5h, hard wall1800초 | 사용자 GPU 교사 단독, 결함8행×최대3회·v5 모든 시도 보존, 학생 학습0 |
| Stage1bW | 약0.5~0.75h(첫 compile/교사 지연 변동, hard wall2700s) | 사용자 GPU full 교사+P076 학생, 최대2업데이트, 고유 진단 checkpoint 예상0.45GiB |
| Stage1cW | 약1.5h(공개 3과제×512와 P10036) | 사용자 GPU 모델2개 순차 평가, 보호 held-out0·문항별 원본 write-once |
| Stage2hW | 4.1분 실측(상한17분) | 이번 지시 한정 Codex 교사-only 12요청, 학생 학습0; GPU 결과는 결과101 후속 절에 귀속 |
| Stage2iWa/Wb/Wc | 각각 4h/1.5h/6h hard wall | **사용자 실행용 대안 세 팔**, 합산 큐 의무 아님; GPU full 교사+P076 학생, 최대5 optimizer 업데이트·체크포인트0 |
| Stage2W | `NOT_ESTIMABLE` | 승인 원천의 실제 유니크 지도토큰·교사 accepted sample 비용·동일평가 확인 후 산정 |

## 7. 실행 파일·사전 점검

- Stage1aW: `run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh`는 결과101의 재현명령과 Git 이력으로 보존 후 삭제. 사용자 번역16건·완결9/16, 문턱12 미달 exit8; v1 덮어쓰기 금지.
- Stage1bW: `run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh`는 결과101/ Git 이력 보존 후 삭제. 상류 미달 check-only 중단·학생학습0, 원시 exit9 분류 결함→후속 CPU HOLD8 수정.
- Stage1aWb/Wc: 두 완료 런처는 결과101·Git에서 복구 가능하며 삭제. Wb sandbox 차단으로 모델0, Wc 승인 GPU 경로4쌍×2팔 종료0·v2 기록; 학생학습0.
- Stage1dW: 완료 런처는 결과101·Git 보존 후 삭제. 교사 교정형3/3 형식 통과이나 새 수치오류1, 자동 학습수락0.
- Stage1fW: 사용자 실행·결과101 §10에서 교정형16/16 형식 PASS·답안 결함8을 회수했다. `run_P106B_Stage1fW_teacher_repair_full16-done.sh`는 재현명령과 Git 이력 보존 뒤 사용자 승인 삭제 조건을 별도로 판정한다.
- Stage1gW: 역사 SH는 결과101 §11에 재현명령과 원본을 보존하고 완료 표기로 전이한다. 사용자 실행8행 중 lint7/8로 사전 문턱 실패; 재실행은 같은 v5에 하지 않는다.
- Stage2a~gW: 교사 내용↔코드 소유 양식·코퍼스 비용·공개 job deck·소형 학생 배선의 각 독립 게이트 SH가 존재한다. Stage2eW 공개 job deck은 2026-09-28 CPU로 실제 생성·SHA 검증했지만 교사 출력이나 학생 품질은 아니다. Stage2c/d/f/g는 각 선결 버전의 사용자 실행 전까지 E2E `NOT_RUN`이다.
- Stage2hW: 이번 지시의 명시적 단기 CPU+GPU 허용으로 교사-only 12요청을 직접 실측했다. v9 write-once 원본과 별도 runlog를 결과101에 회수한다. **학생 온라인 5회가 아니다.**
- Stage2iWa/Wb/Wc: 사용자 요청으로 세 effort별 SH·분리된 v10 output·write-once partial 기록을 준비한다. GPT는 세 팔을 직접 실행하지 않는다. 새 smoke와 Stage2eW job deck SHA, GPU idle/VRAM, 정확 부모/tokenizer 선결이다. A/B/C 중 하나의 결과만으로 다른 팔이 PASS한 것으로 승격하지 않는다.
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
- 2026-09-28: 사용자 새 smoke43/0/0/0 뒤 Stage1fW full16 완결, 교사 자기 `CORRECTED`8/`PRESERVED`8. 직접 검토에서 새 결함8·추가검토4·잠정4라 자동 학습 채택0을 유지한다. 사용자 승인 A로 Stage1gW의 결함8만 프롬프트·진단기 response hook·최대3회 재시도에 연결했다. v5 출력은 새 버전·모델 사용자 실행 전 `NOT_RUN`이다.
