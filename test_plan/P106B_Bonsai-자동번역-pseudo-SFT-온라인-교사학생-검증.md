# P106B — Bonsai 자동번역 pseudo-label SFT와 온라인 교사·학생 연결 검증

> 제안 계기: 사용자 2026-09-27 지시와 추가 질문. [P106 검증형 교사 계약](P106_검증형-교사-정답-계보와-SFT-첫게이트.md)은 독립 검증된 정답만 `ACCEPT`로 부른다. **일반 SFT 데이터가 모두 참이라는 보증은 없고, 전수 사람 승인은 기술적 학습의 필요조건이 아니다.** 이 계획은 P106의 검증형 주장·기존 결과를 고치지 않는 별도 `B` 축이다. 교사 자동번역을 곧바로 학습에 쓸 수 있는지 한정 실험하되 이를 `PSEUDO_UNVERIFIED`로 표시한다.

## 1. 왜 — 질문을 두 개로 나눈다

> 2026-09-30 최신 상태: [결과101 §31](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 새 smoke43/0/0/0 뒤 A1 두 슬롯은 속도비1.140/1.015×·KO형식1~2/4로 exit8, A2는 serial KO4/8에서 exit8·겹침0이다. B2/B4는 한영 각4/4 **형식만 PASS**. C4 실제100행4pass/4optimizer는 SFT-val 개선에도 기존 base full-val+0.018444 악화·고정답8/8 미달이다. f/g0/g는 상류 선결차단으로 실제 통합·후속교육0. 사용자 선택 A로 legacy/chat32 실패 원인 진단과 출력예산·질문수 확대 A1Wb/A2Wb 새 단계·SH를 준비했으며 새 실모델은 NOT_RUN이다. Wh/Wf는 -hold·큐 제외, 300M·교사 정답·지능 채택은 미판정이다.

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

### 3.1 2026-09-28 예측 대조 — 형식 회복과 배선은 확인, 온라인5회는 미완

단순한 태그형 출력은 고정16에서 15건, JSON은14건 완결했으나 **1건 차를 일반적인 형식 우위로 채택하지 않는다**. 소형 학생 배선 Stage2gW는 실제2업데이트·유한 손실/gradient와 새 checkpoint를 만들었지만 13행 반복의 train CE 하락이라 지능 향상 예측의 근거가 아니다. 예상하지 못한 Stage2fW의 **PEG native-format HTTP500**은 독립 단일문항에서도 재현됐고, parser 우회는 `length`/중복 태그 때문에 교육 답 회복이 아니었다. Stage2iWa는 서버500과 원천 수락률 부족으로 optimizer0/5였다. 따라서 ~~형식 gate 뒤 현재 유한 source로 바로 온라인5회 처리율을 잴 수 있다~~는 낙관적 경로를 철회하고 Stage2fWb 보충→Stage2iWd 한 업데이트 기술 게이트→사용자 확정 다원천 C안의 새 계보/권리·실제 토큰 예산 순서로 바꾼다.

2026-09-28 사용자 [Stage2kW/Stage2fWb 결과101 §23~§24](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): source 계보 read-only census 87,361 job은 독립 실행으로 재현됐다. Stage2fWb의 누락7 job 보충은 한국어14/16·영어15/16 **형식** 후보로 각12/16 문턱을 통과했다. 다만 case26 한국어의 native PEG500은 새 seed에서도 두 번 재현됐고 학생 교육/품질은0/`NOT_RUN`이다. 따라서 Stage2iWd의 기술 1업데이트 선결은 열렸으나 교사 완전성, 한영 5:5, 5회 및 300M~600M 확장은 열리지 않았다. 유효하게 등록된 `HOLD` 문항을 문턱 통과라는 이유로 조용히 수락하지 않는다.

2026-09-29 [결과101 §25~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): Stage2kWb 공개 작업표10,528개가 실제 생성됐고 Stage2iWd low는1업데이트, Wb none은5업데이트를 완료했다. 그러나 Wc medium은 **4회 뒤 한국어 원천365개 소진**으로 5회 문턱에 실패했다. 앞서 “현재 유한 source는 5회에 부족할 수 있다”는 예측이 medium에서 확인됐고 none에서는 예상과 달리 수락률이 높아 5회를 끝냈다. 두 팔의 context·출력상한·sampler가 달라 사고 강도 단독 원인을 주장하지 않는다. none/medium manifest의 GDN false는 잘린 서버 오류 버퍼에서 유도한 **무효 계측**으로 교정한다. 어떤 팔도 checkpoint/held-out 품질을 만들지 않았으므로 300M~600M 실질 능력 가설은 아직 열려 있다.

## 4. 단계 설계 — 싼 것부터

### Stage2iWg→Stage2iWh — 새 공개 low·VRAM 계측 수리 1회→5회 (Wg 기술 완료, Wh NOT_RUN)

앞선 **OASST1 low1 Stage2iWd**는1 optimizer·128답·약76.8분에 완료됐으므로 그 조건을 다시 반복하지 않는다. 이번 **공개 Aya Dataset/OASST2 대응 concept5,015개/언어**는 다른 원천이며, We에서 발견한 `nvidia-smi TimeoutExpired`의 sampler fail-open과 Ctrl+C의 `PARTIAL/not_started` 기록 결함을 고친 실물 경로가 새 검증 대상이다. Wg는 `--effort low --variant publiclow1`·thinking sampler(temperature1/top_p.95/top_k20/min_p.05/presence0/repeat1)·ctx3072/max2048, 학생 P076 mean SHA·legacy32·micro8×accum16/ckpt-on·compile를 고정해128개 fresh target/1 optimizer까지만 실행한다. We medium과 원천·context·sampler·실제 적용량이 같지 않아 단일 사고강도 인과 비교로 쓰지 않는다. [모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#best-practices)의 low 미지원/xhigh 유사 주의가 있어 작은 실측 없이 저비용을 보증하지 않는다.

`sample_memory()`는 query timeout 등 계측 실패를 공유 원장에 기록하고 다음 teacher/forward/backward/optimizer 경계에서 **tool fail9**로 중단한다. 처리 중 HTTP는 반환/기존120초 timeout까지 기다릴 수 있다. free<512MiB는 자원 음성8, Ctrl+C는130, source/상한 소진은8이며 각각 partial manifest에 status/reason/phase/pending ID/실제 적용수를 남긴다. 샘플 스레드 실패를 CPU regression에서 주입해 **5/5 테스트**했고 launcher self-test에도 timeout 검출이 있다. 이 정적 통과는 실제 WSL GPU monitor가 안정적이라는 증거가 아니다.

Wg는 새 `v17_online_public1_low/`, Wh는 별도 `v18_online_public5_low/`에 원형·canonical·SHA를20MB 이하 write-once 저장한다. **기존 v15/원본 runlog 삭제나 덮어쓰기 없이** 새 단계로 재시도한다. 실제 템플릿 입력토큰+2048+128≤3072 조건을 만족하지 않는 행은 원문 절단하지 않고 초과 사유로 남긴다. Wh의 모델 로드 전 gate는 Wg의 **동일 public deck SHA·부모/교사 SHA·effort low·ONE_UPDATE_COMPLETE·실제128적용·sample_errors 비어 있음·raw/canonical shard SHA**를 모두 요구한다. Wh는 같은 부모에서 새로 시작해5 optimizer/640답·6h 상한이므로 Wg와 더해6연속 학습으로 부르지 않는다. Wg2h/Wh6h는 상한이지 정식 교육량/성공 예측이 아니다. 두 새 SH의 실제 CPU check-only와 모델 E2E는 구분하며 새 코드 smoke0/0/0/0 뒤에만 GPU 실행한다.

**기존 medium 보류:** We 실험 시도는 -done으로 이관하지만 검증 PASS 아님, 미실행 Wf SH는 사용자 지시로 HOLD 보존한다. 데이터셋 삭제/medium 학습 재개는 이번 범위에 없으며, 향후 자원 여유와 low의 품질 부족이 실측된 뒤 사용자와 다시 결정한다.

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

사용자는 120 optimizer 업데이트를 즉시 돌리지 않고 **5회만 먼저 실측**한 뒤 결과로 다시 결정했다. 이후 직접 실행은 하지 말고 아래 세 조건을 각각 SH로 준비하라고 지시했다. [공통 진단](../scripts/diag_p106b_online_rate5.py)은 Stage2e의 공개 v3 **`OpenAssistant/oasst1` 단일턴·영어 원천** 중 길이 상한을 통과한 365개 concept의 영/한 쌍을 고정 순서로 읽는다. ko는 번역, en은 원답 교정이다. 다섯 optimizer 업데이트 각각 micro8×accum16을 채우려면 **새 교사 출력이 수락된 640 대화**가 필요하다. 한 microbatch마다 새 출력8개를 요청하고 언어를 교대로 바꾼다. 같은 원천 concept의 영/한 출력은 쌍을 이루므로 **640개 독립 concept는 아니다**. 실패 출력은 새 source로 대체하되 언어당 고유 후보365개를 소진하면 `exit8`이며, 실패를 반복 seed로 감추지 않는다.

**2026-09-28 원천 계보 정정:** 기존 설명의 `OASST2`는 잘못이다. Stage2a/c/d의 고정16은 `OpenAssistant/oasst2`이지만, Stage2e 작업표는 [공개 v3 manifest](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)에 연결된 `OpenAssistant/oasst1`과 `CohereLabs/aya_dataset`에서 왔다. Stage2iWa는 그 작업표 중 `oasst`·영어 원문·단일턴 624쌍을 골라 질문/답 각각1200자 이하로 더 줄인 **365쌍**이다. 5회에는 한영 각각320개의 수락 답이 필요하므로 후보 수락률≥87.7%가 필요하지만 사용자 초반 원본은33요청 중23형식 후보(69.7%)였다. 서버500을 빼더라도 이 유한 풀만으로 5회 완료를 전망하기 어렵다. Stage2iWb/Wc와 동일 OASST1 pool로 만든 추후 실험은 원천을 숨기지 않고 provenance를 명시하며, 새 OASST2/Aya/사전 안과 직접 한 변수 비교로 취급하지 않는다.

| 구분 | SH | 교사 사고/출력 예산 | 모델카드 sampler | 상한 |
|---|---|---|---|---:|
| A·Stage2iWa | [low](../run_P106B_Stage2iWa_online5_low.sh) | `low`, ctx3072/max2048 | thinking: temperature1, top_p.95, top_k20, min_p.05, presence0, repeat1 | 4h |
| B·Stage2iWb | [none](../run_P106B_Stage2iWb_online5_none.sh) | `none`, ctx1536/max1024 | instruct: temperature.7, top_p.80, top_k20, min_p0, presence1.5, repeat1 | 1.5h |
| C·Stage2iWc | [medium](../run_P106B_Stage2iWc_online5_medium.sh) | `medium`, ctx6144/max4096 | thinking: A와 동일, Stage2h max2048 절단 때문에 출력 예산 확대 | 6h |

[PrismML 공식 모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)는 thinking과 non-thinking sampler를 위처럼 다르게 권장한다. **현재 카드에는 `low`를 지원하지 않으며 xhigh에 가깝다고 적혀 있는데** 로컬 Stage2hW의 `low`는 4/4 완결·medium보다 짧았다. 카드/실물 런타임 차이 가능성이 있어 A를 정식 저비용 reasoning 경로로 가정하지 않는다. `--reasoning auto`와 요청별 top-level `reasoning_effort`를 유지하고 출력에서 사고·최종을 따로 기록한다. 사고 텍스트는 원본 `HF/sft_ready/p106b_teacher_sft/v10_online_rate5_<effort>/raw_*.jsonl`의 sidecar일 뿐 assistant 지도 target이 아니다. 소프트웨어가 교사의 `[[QUESTION]]`/`[[ANSWER]]`/`[[NOTE]]`를 파싱해 canonical 역할·ChatML·assistant-only 마스크를 소유한다.

세 팔은 동일한 P076 B3 mean 부모·legacy32 tokenizer·학생 micro8/accum16/ckpt-on, 모델 compile/default, Muon RMS4+AdamW를 쓴다. 동일한 공개 source/문항 순서를 쓰지만 교사 sampler/사고강도뿐 아니라 ctx/max 출력 상한도 달라 **팔 간 품질 또는 속도 차를 effort 단독 효과로 귀속하지 않는다**. 각 응답의 완료토큰·요청벽시계·format/reject, 학생 업데이트의 teacher/compute/전체벽시계·실제 비패딩 처리/assistant 지도토큰·언어별 토큰·전역 표본 peak와 PyTorch reserved를 별도 기록한다. 모든 시도와 학생 target은 20,000,000바이트 이하 write-once JSONL 샤드/해시 manifest로 남긴다. 시작 다른 GPU compute 앱0/free≥14GiB, 공존 후 free≥2GiB, 중간 free<512MiB·시간 초과·소스 고갈·형식 실패는 부분 이력을 보존하고 `exit8`이다. **체크포인트 저장0·held-out 평가0·정식 `TRAIN_READY`/품질 PASS0**. `exit0`은 이 제한 처리율 gate의 5업데이트 기능 완료일 뿐이다. 5회 결과와 한국어/영어의 실제 비패딩 토큰 비율·교사/학생 속도를 본 뒤에만 120회 온라인 지속 여부, chunk 선제생성/10GB 이하 RAM 버퍼의 필요성을 새 계획으로 결정한다. 이 세 SH를 큐에서 모두 연속 실행할 필요는 없다.

### Stage2jW — Stage2f/Stage2iWa 공통 HTTP 500의 매우 작은 원인 격리 (이번 지시 직접 허용)

2026-09-28 사용자 원본은 Stage2fW 교사-only 패널의 25번째 문항을 기록한 뒤 26번째에서 HTTP 500·`exit9`, Stage2iWa 온라인 low의 교사 응답33건 뒤 다음 요청에서 HTTP 500·`exit8`, 학생 optimizer 업데이트0을 보였다. 두 단계의 기존 클라이언트는 HTTP 오류 본문을 버렸고 Stage2fW는 부분 raw 29행을 남겼지만 manifest를 닫지 못했다. 따라서 **서버가 왜 500을 반환했는지 로그만으로는 확정할 수 없다**. Stage2iWa의 서버 실패를 과학적 음성8로 분류한 것은 도구 분류 결함이고, Stage2fW가 미통과인데 Stage2iWa의 check-only가 이를 선결에서 거부하지 않은 것도 계약 결함이다. Stage2gW의 학생2업데이트는 별도 v7 한국어13행 반복으로 Stage2fW의 성공이나 온라인5회가 아니다.

사용자는 이번 지시에 한해 매우 작은 CPU+GPU 직접 게이트를 허용했다. [Stage2jW 진단](../scripts/diag_p106b_http500_isolation.py)과 [별도 SH](../run_P106B_Stage2jW_http500_isolation.sh)는 **교사만** 두 개의 새 localhost 서버로 올려 각 환경의 실패 직전 입력과 첫 실패 입력을 고정 2개씩, 최대4요청/600초로 한정한다. 기존 Stage2fW 부분 raw SHA `2D395CD2155D04934F13240430B4D566BA621B6871775BCCB4083D8202E7347E`, Stage2iWa 부분 raw SHA `17A3EE87711E78D58FCD4A3BEF3A16662A02BE7BF25A00C4B949C22780EE5146`를 먼저 대조한다. GPU 경쟁 프로세스0·시작 free≥8192MiB에서만 모델을 올리고 출력은 새 `HF/sft_ready/p106b_teacher_sft/v11_http500_isolation/`에 write-once로 남긴다. 학생 로드/업데이트·체크포인트 쓰기·원본 v8/v10 재실행/수정은0이다.

독립변수는 **긴 세션 상태를 없앤 새 서버에서 정확 실패 위치 입력의 HTTP 500이 재현되는가**이다. 서버 `/apply-template`+`/tokenize`의 프롬프트 토큰 수, `ctx/max_tokens`의 명목 합, HTTP 본문 SHA/오류유형, 제한된 서버 오류 줄, 요청 전후·표본 GPU 점유를 기록한다. 두 서버 방식은 long-session 누적상태·학생 공존/학습을 의도적으로 제거하므로 HTTP 500이 **재현되지 않아도 기존 실패를 해결했다는 뜻이 아니다**. 재현되면 HTTP 500은 도구/백엔드 실패 `exit9`로 보고 본문 근거로 입력 초과·메모리·서버 결함을 더 좁힌다. 재현되지 않으면 장시간 상태/학생 공존 여부를 별도 사용자 실행 단계로 확인해야 하고, 출력 상한 축소·자동 retry만으로 원인을 숨기지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage2jWb — peg-native parser 우회 단일 요청, 학생 입력으로 직접 사용 금지

Stage2jW에서 Stage2fW 문항26은 새 서버에서도 HTTP500을 재현했고, 원문 오류 본문은 `The model produced output that does not match the expected peg-native format`이었다. 서버 토큰 preflight의 입력817+출력상한4096은 ctx6144보다 작고, 응답 뒤 GPU free는 약8.5GiB였다. 따라서 **그 재현 사례**는 긴 세션 누적상태·학생 공존·명목 컨텍스트 초과나 관측 OOM이 필수 원인은 아니라는 반례다. 반면 Stage2iWa의 한국어 소스23은 학생 없는 새 서버에서 HTTP200이라 원래 온라인500의 원인을 아직 모른다.

이번 승인된 초소형 진단 범위에서 [Stage2jWb](../run_P106B_Stage2jWb_peg_parser_bypass.sh)는 Stage2f 문항26 하나만 동일 모델/소스/seed/sampler/ctx/max로 재생하고 서버의 `--skip-chat-parsing`만 바꾼다. [llama.cpp 서버 안내](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)는 이 옵션이 서버의 chat/reasoning/tool 파싱을 건너뛰어 원형 응답을 `content`에 담는다고 설명한다. 실행해 HTTP200·원형 출력이 나오면 **서버 native 파서와 실제 모델 출력의 불일치**로 원인을 더 좁힐 수 있다. 그러나 사고와 최종답 구분도 비활성화되므로 원형 `content`는 **학생 assistant target이 아니며** 한국어/영어 tagged 필드만 임의 정규식으로 뽑아 학습시키지 않는다. 원형 응답은 새 무시된 `HF/sft_ready/p106b_teacher_sft/v12_peg_bypass_case26/`에 write-once로 남기고 실행 로그에는 SHA·구조 표지 수만 적는다. 단일 요청/최대300초·학생0·checkpoint0이고, 서버 우회가 형식·사실 품질 해결이라는 주장은 금지한다.

### Stage2fWb — 옛 29시도 SHA 참조 + 빠진 7문항만 새 버전에서 보충

사용자 Stage2fW는 32개 고정 job 중 **25번 문항까지 29시도**를 남기고 26번에서 서버의 PEG native-format HTTP500으로 종료9였다. old partial 원본은 손대지 않는다. [보충 진단](../scripts/diag_p106b_bilingual_recovery.py)과 [별도 SH](../run_P106B_Stage2fWb_bilingual_teacher_recovery.sh)는 정확 old SHA/29시도/1~25번 job 매핑을 대조하고 **26~32번 일곱 문항만** 새 `HF/sft_ready/p106b_bilingual_v2/teacher_recovery/`에 요청한다. 기존 29시도는 복사하지 않고 SHA 참조로 결합해 언어/주제/학생 비패딩·assistant 지도 토큰 분모를 재계산한다. 신규 답은 교사 tagged 형식→코드 소유 canonical/ChatML의 1024 위치·중복 화면까지 검사하되 자동 교육 채택은0이다.

Stage2jWb 단일 문항은 `--skip-chat-parsing`에서 HTTP200이지만 **max4096을 모두 사용해 `length`로 끝났고 tagged QUESTION/ANSWER가 반복돼 파서 완결이 아니다**. 따라서 서버 파서를 우회한 원문을 학생에게 전달하지 않는다. 원래 native 파서는 유지하고, 정확한 `peg-native format` 500만 **해당 문항의 거부된 교사 시도**로 기록·다른 seed에서 최대 한 번 재요청한다. 두 번 모두 실패하면 그 문항을 거부하고 다른 고정 job을 계속한다. 알 수 없는 HTTP/transport 실패는 도구 실패 `exit9`로 멈추며 부분 시도·오류본문·서버 진단과 manifest를 보존한다. 형식/길이/중복 거절도 감추지 않는다. 결합 패널의 사전 문턱은 한영 각 후보≥12/16, hard wall1800초, 기존 P106B의 **형식/코드 래핑 가능성만** 판정한다. 이 7문항 보충은 같은 32개 입력을 처음부터 다시 뽑는 것보다 교사 비용을 줄이지만, 새 서버/날짜·실패 처리 정책이 달라 old Stage2f와 시간비 인과 비교는 금지한다.

### Stage2iWd — 옛 OASST1 원천의 온라인 백엔드 1-update 재시험 (조건부)

Stage2iWa는 **학생 optimizer 0회**로 종료했고, HTTP500 응답 본문·서버 진단을 기록하지 않아 그것이 Stage2f의 PEG 출력 불일치와 같은 실패인지 모른다. [후속 코드](../scripts/diag_p106b_online_rate1.py)와 [별도 SH](../run_P106B_Stage2iWd_online1_backend.sh)는 **Stage2fWb 한영 각 후보≥12/16·manifest SHA**를 모델 로딩 전에 요구하고, 같은 P076 부모/legacy32·micro8×accum16·low thinking sampler·OASST1 finite source에서 **1 optimizer 업데이트**까지만 진단한다. 정확 PEG native-format 500은 해당 교사 시도만 거부·별도 SHA/오류본문 기록하고 다음 고유 source로 가며, 다른 서버/전송 오류는 부분 원본 보존 후 **도구 실패 exit9**다. 새 `v13_online_rate1_low_backend/`에 모든 시도·후보와 실제 업데이트에 들어간 generation ID를 구분해 write-once 저장하고 checkpoint는0이다. `Stage2iWa` raw의 `accepted_for_training=true` 23건은 실제로 optimizer가0회여서 **선정된 미적용 후보**였으며 새 코드에서 같은 오해를 반복하지 않는다. 이 1회는 OASST2/Aya/사전 혼합 5회 목표가 아니라 **동시 교사+학생 호출 경로의 수리 검증**이다. 사용자 재실행·새 smoke 이전에는 E2E `NOT_RUN`이다.

### Stage2iWe→Stage2iWf — 공개 다원천 medium 1회 선결 뒤 5회 (2026-09-29 사용자 A안 승인)

Stage2iWc의 `exit8`은 **한국어 OASST1 단일턴365개 소진**, 코드 예외가 아니다. 같은 원천을 무제한 재질문해 실패를 감추지 않는다. 이미 Stage2kWb에서 만든 공개 전용 Aya Dataset/OASST2 **train 대응 concept5,015개/언어**와 SHA 고정 샤드만 새 코드가 읽는다. `protected_locator=null`·`CARD_ONLY`·source repo/revision/원본 SHA/parent concept/split을 엄격히 확인하며 보호 사전·사전 파생물은 열거·입력하지 않는다. source는 원문 언어가 EN 또는 KO일 수 있어 target이 같으면 `repair`, 다르면 `translate`이며 교사는 content만 쓰고 canonical ChatML/assistant-only 마스크와 계보는 코드가 소유한다. source 권리 카드 상태가 곧 formal `TRAIN_READY`가 아니다.

새 [Stage2iWe SH](../run_P106B_Stage2iWe_online1_public_medium.sh)는 medium 모델카드 sampler·ctx6144/max4096, 같은 P076 부모·legacy32·micro8×accum16/ckpt-on에서 **1 optimizer 업데이트/128개 신선 후보**만 실행하고 2h hard wall·write-once v15·checkpoint0으로 제한한다. 교사 `/apply-template`→`/tokenize`의 실제 입력 토큰과 `input+4096+128≤6144` 조건을 각 job마다 확인한다. 초과/12k payload 한계 행은 `COMPRESSION_REQUIRED`/HOLD로 raw에 남기고 무단 절단하지 않으며, 미확인 token API 오류는 tool fail9로 분리한다. 교사 답이 완결돼도 사실성·개인정보는 아직 미검증이다. 출력을 직접 학습하는 범위는 **진단용 pseudo-label**에 한정한다.

Stage2iWe 사용자 원본 manifest가 **동일 공개 deck SHA·ONE_UPDATE_COMPLETE·실제1회**이면 당시 Stage2iWf 구현의 check-only가 통과하도록 선결을 코드로 묶었었다. 하지만 We는 완료하지 못했고 사용자는 medium 보류를 유지한다. [보존 Wf SH](../run_P106B_Stage2iWf_online5_public_medium-hold.sh)는 직접 실행해도 즉시 HOLD8이며 현재 큐의 실험이 아니다. 재개되더라도 Stage2iWe의 교사답이나 학생 가중치를 재사용하지 않고 같은 부모에서 새 단계로 준비해야 한다. 5회 통과는 기술 처리율/원천 수급 관측뿐이며 **OASST1 none 5회와 원천·길이 선별이 달라 인과 속도·품질 비교 금지**다. 300M/600M, 지능 상승, 멀티턴 능력은 별도 평가·권리·오답 분석 전 `NOT_RUN`이다.

### Stage2kW — 사용자 선택 C: Aya Dataset·OASST2·국립국어원 다원천을 계보별로 묶는 읽기 전용 계약

사용자는 다원천 C안을 선택했지만 A안의 비용/원천 분리와 B안의 사전 권리·다의어 주의도 보존하라고 했다. [원천 관리자](../scripts/build_p106b_multisource_deck.py)와 [CPU 읽기 전용 SH](../run_P106B_Stage2kW_multisource_lineage_census.sh)는 다음 사실을 **같은 집합으로 뭉개지 않고** 별도 계보로 기록한다.

| 층 | 고정 원천·선별 관측 | 생성 역할 | 독립성·선결 |
|---|---|---|---|
| Aya 영어 | 공개 v3의 `CohereLabs/aya_dataset` revision `f9ea0458…`에서 영어 단일턴 train1363/val76개. `aya_collection`과 **다른 저장소**다 | 원 영어 QA의 교정 EN + 교사 번역 KO | 같은 `parent_concept_id`, 두 언어를 독립 사실2건으로 세지 않음. 카드 Apache-2.0만으로 사람 품질/PII PASS 아님 |
| OASST2 | 별도 `OpenAssistant/oasst2` revision `179dd21…`의 reviewed 단일턴 영어5400·한국어5. 공개 v3 첫 질문 겹침/자체 중복 제외 후 영어3824·한국어1개 계열; 영어 질문/답 각각1200자 이하로 제한하면 새로운 계열2018개 | 원 EN 교정+KO 번역; 원 KO는 한영 양방향 **canary 1개**만 | OASST1 v3와 이름을 혼동하지 않음. OASST2 reviewed EN 멀티턴2378은 이 Stage2k **단일턴** 작업표에 자동 편입하지 않음 |
| 국립국어원 JSON | 지정 2026-08-19 JSON11개, 뜻풀이76,833개/고유 표제 target ID53,671. `concept/word-*.txt` 27개와 TXT2는 표제어 **선정 우선순위/교차검증**이지 새 독립 QA 행이 아님 | 의미 ID·품사·동형어·용례 근거로 KO QA; 실제 KO 교사 답이 생긴 뒤 별도 EN 번역 child | 현 작업표는 원문 뜻풀이/용례를 출력하지 않는 locator76,833건만 설계. `target_code+lexicalUnit+sense+file/ordinal`로 ID 충돌 회피; 사이트 CC BY-SA2.0 KR 정책과 로컬 판본 파생·배포 계약 별도 검토 |

Stage2kW 읽기 전용 실사에서는 public Aya 양언어 job2,878개, OASST2 양언어 job7,650개, 사전 한국어 의미 locator76,833개 등 **87,361개 job**을 계수했고 사용자 [원본 결과101 §23](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 같은 수를 재확인했다. 이것은 **교사 답안/독립 지식/학습 토큰 수가 아니다**. 사전 뜻풀이 하나에서 한국어 QA를 생성한 뒤 영어 번역 child를 만들 때도 부모 의미 ID와 train/val split이 고정된다. 공개 Aya의 기존 v3 split을 유지하고 OASST2/사전은 원천 concept hash로 *생성 전에* split한다. 정규화된 첫 질문이 v3와 겹치는 OASST2는 제외한다. 모든 job은 source repo·revision·원본 SHA·object/sense ID·변환종류·부모 concept ID·언어·rights 상태를 갖는다. **당시 Stage2kW는 읽기 전용**이었으며 구 통합 `--execute` 설계의 공개+사전 locator 같은 출력 디렉터리와 보호 source rights attestation는 실제로 실행되지 않았다. 사용자 권리 분리 회신 후 이 구 출력 경로는 폐기하고, 아래 Stage2kWb의 공개 job만 별도 네임스페이스에 쓰도록 변경한다. 사전 파생 원문·후보·학습 corpus는 여전히 만들지 않았고 별도 격리/권리 판단 대상이다.

### Stage2kWb — 공개 원천만의 분리 job deck, 사전 계열은 읽기도·쓰기에도 포함하지 않음

Stage2kW의 87,361건 전체를 한 데이터셋으로 출력하면 사전의 CC BY-SA 계열 locator가 공개 Aya/OASST2와 같은 산출물에 들어간다. [새 공개 전용 관리자](../scripts/build_p106b_multisource_deck.py)의 `--execute`는 `HF/sft_ready/p106b_public_job_deck_v1/`에 **Aya Dataset 2,878 + OASST2 7,650 = 예상10,528개** public source job만 write-once 20,000,000B 이하 JSONL 샤드로 기록한다. `source_family/repo/rights_status/protected_locator`의 네 조건 중 하나라도 사전·미지 출처이면 출력 전에 거부한다. **이 실행 모드에서는 지정 보호 사전 폴더를 읽지 않는다.** `--check-only`는 기존 Stage2kW와 같은 87,361 job read-only 합계이며 공개 전용 실행과 동일한 분모로 혼동하지 않는다. 다음 단계의 실제 교사 답/학생 target은 아직0이다.

[별도 사용자 CPU SH](../run_P106B_Stage2kWb_public_only_job_deck.sh)는 새 smoke PASS 뒤 self-test→격리 회귀→공개 `--execute`만 실행한다(예상≤0.1h, GPU0). 출력 디렉터리가 이미 있으면 덮어쓰지 않고 실패하며, 샤드 SHA·행수/총byte와 공개 source id/split을 검산한다. 사전 계열의 미래 물리 네임스페이스는 `HF/sft_ready/p106b_krdict_by_sa_quarantine_v1/`로 **별도 예약만** 하며 이번 SH가 만들지 않는다. CC BY-SA로 분리된 데이터 행을 공유할 때의 표시·동일조건, 개념만 사용한 독립 새 행인지 여부, 모델/출력 공개 때의 권리 판단은 각각 다른 문제다. 폴더 분리나 교사 문장 변환이 자동 법적 면제라는 주장은 하지 않는다. 공식 [사전 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)과 [CC BY-SA 2.0 KR 법문](https://creativecommons.org/licenses/by-sa/2.0/kr/legalcode.ko)은 저작물 변형 배포/편집물 구분을 명시하며, [CC의 AI 학습 해설](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)은 모델·출력의 실제 표현 재현과 공개 맥락을 별도 판단 대상으로 둔다. 이 단계는 법률 자문이나 사전 파생 학습 승인이 아니다.

### 사전 파생 3안·모델 원문 재현 검증 — 사용자 1안 선택, 실제 생성 `NOT_RUN`

사용자 제안대로 **사전 파생 행을 공개 자료와 다른 디렉터리·manifest에 저장하고 Git에서 제외**하는 것은 혼합 방지의 첫 단계다. 다만 훈련 로더의 `source_family/rights_status` allowlist와 같은 concept/문장 교차 검사, 원본→교사 후보→검토본의 SHA/부모 계보가 없으면 파일을 복사·재직렬화할 때 다시 섞일 수 있다. 현재 공개 전용 writer의 synthetic 회귀는 보호 사전의 읽기·출력0만 증명한다. 아직 사전 파생 writer/학습 로더 소비 경계는 없다.

| 후보 | 만들 데이터 | 라이선스·품질 경계 | 비용·권장 |
|---|---|---|---|
| **A: CC BY-SA 격리 후보** | 뜻풀이·용례를 교사에게 주어 만든 질문/답·교정본을 `p106b_krdict_by_sa_quarantine_v1`에 별도 저장, 원본 표현과 생성 이력 기록 | 사전 표현에서 파생된 행으로 **보수적으로** 분류하고 출처·변경·CC BY-SA 표지를 유지; 공개셋/일반 trainer에 자동 병합 금지. 학습모델 자체에 동일조건이 자동 전염된다는 주장도, 반드시 무관하다는 주장도 하지 않음 | 가장 빠른 한국어 근거형 pilot. 사용자 분리 요청과 일치하나 배포·모델 출력 검토가 남음 |
| **B: 의미요소→새 예문→새 정의 재합성** | 첫 교사가 원 `표제어+정의`에서 의미·품사·조건을 추출하고 새 예문 작성. **다른 문맥/작성자**는 원 정의·원 예문을 보지 않고 `표제어+새 예문`으로 정의를 다시 쓴다. 세 번째 검토자가 새 세트의 뜻·용례 일치 확인 | 사용자 제안의 이중 재구성을 개선했지만 단계1이 원표현을 보므로 법적 독립성은 자동 보증 안 됨. 원문/재합성본은 별도 계보로 두고 드문 장문·고유 문구 겹침과 의미왜곡을 검토할 때까지 A와 같은 격리 상태 | 표현 거리 증가 가능, 교사 비용·환각/뜻 변화 위험 증가. 독립셋 승격은 별도 사람/권리 검토 후 |
| **C: 독립 원천 clean-room** | 표제어·일반 개념만 선정하고 독립 사용허락 원천 또는 원문을 보지 않은 작성자가 뜻·예문을 새로 만든다 | 사전 예문·정의는 작성자/교사 입력으로 전달하지 않으며 출처·질문 분포를 별도로 기록. 독립 창작 주장도 최종 표현/권리 검토 필요 | 법적 분리 설명은 가장 명료하지만 한국어 뜻의 정확한 sense 대응과 제작 시간이 비용 |

**모델 재현성 점검 설계(미실행):** 같은 부모/토크나이저/질문셋에서 사전 미사용 대조와 사전계열 사용 후보를 비교한다. (i) 원문 중 **드물고 긴** 예문 앞부분을 준 완성 질문, (ii) 원문 문구를 주지 않은 의미 질문, (iii) 동일 길이·주제의 공용표현 및 사전 외 독립 문장 대조를 나눠 생성한다. 원문/출력의 연속 일치 최장 길이, 드문 n-gram·근사 표현을 **후보 추출**에 쓰고 문장 길이·표제어 빈도·공용표현 배경율을 맞춰 오탐을 보정한다. [GPT-3 중복 분석](https://arxiv.org/pdf/2005.14165)은 짧거나 흔한 문구의 오탐을 지적했고, [암기 계측 연구](https://arxiv.org/abs/2202.07646)는 중복·프롬프트 길이에 따른 원문 재현 차이를 보고했다. 높은 점수 행은 독립 사람이 원문·출력의 창작적 표현/맥락을 직접 검토한다. **n-gram 일치만으로 침해·파생 판정하지 않으며 0건 탐지도 암기/권리 문제 부재를 증명하지 않는다.** 보호 예문과 생성 원답은 ignored 격리 저장에만 두고 Git·일반 벤치 원본에는 넣지 않는다.

사용자는 **A안부터** 진행하고, B안의 새 예문/새 정의 후보와 A안·원문 간 표현 유사성은 **사후 비교**하기로 확정했다. [격리 어댑터](../scripts/p106b_rights_isolation.py)는 사전 원문 없이 합성 fixture만 사용해 다음 보조 계약을 구현했다: 원본 locator+SHA를 가진 `krdict` job만 받아 교사 내용의 질문/답을 코드 소유 canonical로 감싼 다음 `CC_BY_SA_2_0_KR_CANDIDATE`·출처 URL·`training_eligible=false`·`independent_expression_status=NOT_DETERMINED`를 붙인다. 이것을 다시 `P106B_RESTRICTED_CANDIDATE_V1`의 **상위 envelope**로 감싸, 일반 `load_canonical()`이 경로만 받아 학습셋으로 오용하면 `messages` 부재로 실패한다. 1~128행 write-once pilot writer는 오직 `HF/sft_ready/p106b_krdict_by_sa_quarantine_v1/candidates/`에만 기록하고 공개 job 디렉터리와 다른 SHA 샤드를 쓴다. 합성 CPU 자기시험은 이 격리·재입력 실패를 확인했으나 실제 사전 뜻풀이/용례를 읽거나 교사에게 전달하거나 파생 행을 만들지 않았다. 현재 저장소 `.gitignore`·`.agents/project.json`은 `HF/`를 제외하지만 Git 강제 staging 위험까지 자동 제거하지는 않으므로 향후 커밋은 명시 경로만 검토한다. A안의 실물 교사 후보 생성·원문/후보/B안 비교와 모델 출력 유사성 검사는 별도 사용자 실행/계획 선결이며 `NOT_RUN`이다.

교사관리 코드의 `teacher_admission()`은 향후 같은 localhost 교사 서버의 `/apply-template`·`/tokenize`에서 정확 입력 토큰을 받은 뒤 `DIRECT/COMPRESSION_REQUIRED/HOLD`를 반환한다. `wrap_teacher_answer()`는 **교사가 작성한 최종 태그 본문**만 canonical로 감싸고 source repo/revision/SHA·object/sense·변환 종류·부모 concept ID·권리 상태를 메타데이터로 고정한다. 교사 사고는 외부 raw sidecar 참조일 뿐 현재 학생 loss 대상이 아니다. 출처가 사전인 job은 승인된 조건에서도 영문 번역을 **같은 concept의 자식**으로 생성하지, 독립 지식 건수로 세지 않는다. 이 함수 계약의 합성 CPU 자기시험은 PASS지만 다원천 교사 실제 호출/정답성은 `NOT_RUN`이다.

**사용자 A안 확정 — 1,200자 규칙 폐기:** Stage2iWa의 `질문≤1200자·답≤1200자`는 `ctx3072/max2048`에서 약1024 입력토큰을 남기기 위한 거친 프록시였다. 이는 모델/토크나이저의 절대 제한이 아니다. Stage2jW의 **원천 약2461자**도 교사 chat template 입력817토큰으로 `817+4096<6144`였고 실제 실패는 PEG native-format 불일치였다. 새 관리자에서는 문자 기준으로 미리 버리지 않고, 요청 직전 서버 `/apply-template`·`/tokenize`의 **실제 입력토큰 + 출력상한 + 안전여유128 ≤ context**면 원문 그대로 쓴다. 미달만 `COMPRESSION_REQUIRED` 별도 child 작업으로 보내며 원문을 조용히 자르지 않는다. [교사 `compress_qa` 작업](../scripts/p106b_teacher_format.py)은 질문 의도·답 사실·부정·고유명사·숫자·단위·형식 제약 보존을 요청한다. [원천 관리자](../scripts/build_p106b_multisource_deck.py)는 **먼저 원천 언어에서** 압축 QA를 만들고, 숫자·부정/필수 리터럴의 보수적 누락 검사를 거친 후에만 원래 목표 언어의 번역/교정 child를 생성하도록 부모 concept/split/생성 ID를 계승한다. 한국어 번역 목표를 원천 영어 압축 단계에 섞지 않는다. 이는 **의미보존의 충분조건이 아니므로** 압축본의 원문 대조/표본 품질 확인 전 학생 target으로 자동 채택하지 않는다. 너무 긴 입력이 압축 프롬프트에도 안 들어가면 문단 근거 분할 또는 HOLD이지 무근거 앞부분 절단이 아니다. 지금은 이 함수 계약의 CPU fixture만 PASS이며 실제 teacher 압축·새 한영 토큰 균형은 E2E `NOT_RUN`이다.

**규모 경계:** 사전76,833 의미 ID와 공개 약5,264 원천 concept을 각각 한 번 100토큰 대화로 바꾸어도 대략8M토큰 규모의 거친 계산에 불과하다. 300M 비패딩 처리토큰의 4epoch 하한인 고유75M에는 한참 모자랄 수 있다. 5회 처리율·생성 답 길이·거부/근사중복률 실측 전에 이 작업표만으로 300M/600M 완주 가능하다고 주장하지 않는다. 사전 한국어 자산은 [국립국어원 공식 저작권 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)의 표시/동일조건을 로컬 판본·파생물/배포 방식에 적용하는 결정을 별도로 받아야 한다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

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

### Stage3 — 사용자 승인 생산성·재사용·통합 게이트 (2026-09-30 준비, 모델 NOT_RUN)

**선택 회수:** A1/A2 모두 독립 테스트, B2→4, C4 실제4epoch, 모두 해당 문턱을 통과하면 통합1 optimizer다. 통합은 C reader의epoch1만 쓰고4epoch 완료로 부르지 않는다. 그 다음 통합에서 보존한 자료를 별도 train/val로 나눠 작은4epoch 교육을 준비한다. 보호 원천은 연결하지 않으며 학습량을 맞추기 위한 수백회 재사용도 하지 않는다.

| 단계 | 독립 질문·설계 | 선결·판정 | 예상 / hard cap |
|---|---|---|---|
| Stage3c0W | exact v17 raw/canonical SHA128행을 concept와 정규화 첫질문 모두 겹치지 않게 분할, train100/val28 | 새v19 존재하면 중단; 교사·학생 모델0 | CPU0.1h |
| Stage3aW A1 | 한 교사 weight copy,1→2→2→1slot ABBA, 각 KO4/EN4·같은 seed, slot당ctx3072/output2048; 학생 부모는 상주 | 두 순서 쌍 모두 유효 student tok/s 비율>1.05,각 언어≥3/4·2slot 수락행 수 감소 없음; 별도 active 학생16행 자원 업데이트·NVML/GDN 정상 | GPU0.9h /2h |
| Stage3bW A2 | 같은16 source의 serial 대1slot producer/consumer 겹침. 원형/후보 durable 저장 후 최대32행·20MB RAM queue; 첫8행부터 학생 계산 | 각 언어≥6/8, 실제 teacher/student 시간구간 overlap, 건강한 계측/finite gradient. 실효 배치는최대16행, 부분누산2micro 이하임을 공개 | GPU0.8h /2h |
| Stage3dW B2 | 한 질문→짧은 답/짧은 설명2개. 한 응답 순차 decode, 두 독립 sequence가 아님. ctx6144/output4096 | KO/EN 각각≥3/4 complete 그룹,2/4 exact태그·학생≤1024·canonical/마스크 검사. 의미모순 판정은 사후 원답 검토 | GPU0.5h /1h |
| Stage3eW B4 | B2 통과 뒤 같은질문4개 스타일, ctx12288/output8192 | B2 source/code 일치, 동일 형식/자원 문턱. B4도 통합 선결; 첫 통합은 자원통제를 위해 더 작은B2 고정 | GPU0.7h /1h |
| Stage3cW C4 | 원부모에서 새v19 train100행을 정확4pass, epoch마다shuffle; 같은질문/개념 전체는 같은split. micro8/accum최대16·ckpt-on | 실제4 optimizer·비패딩78,260/지도57,852; 짧은100행 그룹을128로복제하지 않음. parent/after full-val2,929crop·SFTval·고정답8×2. base CE악화≤.1nat, SFTval악화≤.1nat는 **운영pilot 안전선** | GPU0.4h /2h |
| Stage3fW 통합1 | A1/A2/B2/B4/C4 현재 code·source·parent·tokenizer SHA PASSED 후,1서버2slot·slotctx6144·B2·bounded queue·Cepoch1 보존64+새변형64 | micro8×accum16·한 optimizer만, 옛v17 concept는 새생성에서 제외; fresh KO32/EN32·형식/손실/gradient·NVML/GDN. 체크포인트0·품질 NOT_RUN | GPU0.8h /2h |
| Stage3g0W→gW | 통합128행을 새v25 concept/prompt-disjoint split로 준비한 뒤 원 P076 부모부터 정확4pass의 소형 실제 SFT | 통합1 PASSED와 SHA가 선결; 같은 full-val·SFTval·고정원답/망각 기록·새ckpt/JSON. 실제처리토큰/부분유효배치 공개 | CPU0.1h+GPU0.4h /학습2h |

A1의1.05 문턱은 이 pilot의 작은 order/noise 여유이며 통계적 신뢰·모델 품질 자가 아니다.2slot은 총context를2배 배정하므로 같은 **slot별** budget 대조이지 같은 총KV 크기 대조가 아니다. A1 active 자원 업데이트는 속도 ABBA를 끝낸 뒤 별도 수행해 optimizer/allocator 상태가 중간에바뀌는 교락을 피한다. A2는 serial-first/cold compile와 생성문구 차이가 남으므로 전체wall 비율을 제시해도 원인적 속도 채택은 하지 않는다. 통합에서ctx/variant길이 증가에 따른 자원은 별도로 다시 fail-closed 확인한다.

**자료/교육 계약:** teacher thinking은 raw sidecar에만 남는다. tag 파서와 canonical/ChatML·assistant-only mask는 코드가 소유하며 교사에게 JSON·학생토큰ID를 만들게 하지 않는다. 모든 다중답은 같은 `parent_concept_id/source_split`·변형번호로 묶고 신규 지식 수를 부풀리지 않는다. 새 버전 v19~v25·실제 사용된 generation ID·source/SHA·처리토큰·수락/거부·code 계약을 남긴다. partial/interrupt도 원형을 버리지 않으며 기존 version을 지워 재실행하지 않는다.

**조건/비교 한계:** 학생은 P076 mean SHA `41036721...F5D00A71`, legacy32 SHA `3A69001E...52C48E3`, Muon RMS4×4+AdamW·lrs1e-4/4e-4·WD0·KDoff·ckpt-on/compiledefault다. ChatML SFT 형식을 쓰지만 chat32 특수토큰 단일ID 계보 모델은 아니며 새tokenizer를 옛parent에 잘못 끼우지 않는다. C4 checkpoint 태그 `p106b_s3c_repeat4_s1337`, 후속 `p106b_s3g_followup4_s1337`은 새출력/미존재 guard를 갖는다. 일반registry의 전 `runs/` JSON 조회는 승인범위 밖이라 하지 않고 정확 두 output/metadata 미존재·기준표 tag 예약·기존 result/계획 비교로 대체했다. pretrain 풀2× 규칙은 이 의도적4epoch SFT의 독립일반화 증거가 아니다.

**반복 근거:** P087 결과073의4배는 큰300M 풀에서 복원추출1.2B노출이었다. 그 조건에서 과적합 신호가 없었지만 이100행 assistant-only exact4pass와는 pool/목적/optimizer가 다르다. 따라서 C4의 held-out CE·base full-val·실제 답안·노출횟수 자체 기록을 생략하지 않는다. 새 SH9건의 CPU회귀10/10은 운영계약만 확인했고 실제 속도/OOM/교육효과는 NOT_RUN이다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3aWb/3bWb — 2026-09-30 사용자 A 승인: 옛 실패를 보존한 별도 재시험

A1의 원본 v22는 두 쌍 중 첫 속도비1.140×만 1.05를 넘었고 역순은1.015×, KO형식은1~2/4였다. A2의 v23은 고정16교사 요청 중 KO4/8·EN6/8이라 serial에서만 partial10행과 학생 일부 backward를 남기고 optimizer/실제겹침0이었다. **이것은 도구 전체 실패가 아니라 사전 형식 문턱의 음성**이다. 그러나 A2 최상위 `arms=[]`는 partial serial 원형을 보여 주지 못한 기록 결함이므로 새 코드에서는 `serial/arm_manifest.json`이 있으면 상위 요약에도 `partial_arm=true`를 남긴다. 기존 v22/v23 JSON·문턱은 수정하지 않는다.

| 새 단계 | 변경축·불변축 | 사전 판정과 비용 |
|---|---|---|
| Stage3aWb | 한 교사·같은 공개원천/부모·low sampler, **질문군 언어당4→16 / slot당ctx3072→6144 / output2048→4096**; 새 v26, ABBA1→2→2→1 | 각 팔 KO·EN 각각≥12/16 형식 완료, 두 순서쌍의 유효학생자료 tok/s 모두>1.05, 두 슬롯에서 완결행 감소0, 활성학생16행 공존·GDN/VRAM 계측 정상. ⚙1.5h·hard2h. 형식 회복·속도 증가/OOM안전은 사용자 E2E 전 NOT_RUN |
| Stage3bWb | 같은 원천/부모·low, **질문군 언어당8→16 / ctx3072→6144 / output2048→4096**; 새 v27, serial→durable producer/consumer | serial·overlap 각 KO·EN≥12/16, 실제 교사/학생 실행구간 겹침, 표본VRAM·finite loss/gradient. 각 팔 최대32행의 부분누산이며 128행 본학습·인과적 속도채택은 아님. ⚙1.0h·hard2h. E2E NOT_RUN |

출력예산과 표본을 **동시에** 바꿨으므로 옛 v22/v23과의 속도 차이를 한 변수의 효과로 귀속하지 않는다. 큰8문항 B2/B4가 각4/4였다는 관측은 출력 상한 가설의 근거일 뿐 확증이 아니다. 새 A1도 문구·학생대화 길이가 팔별로 달라 순서교차와 수락행 수를 함께 본다. A2는 고정 serial-first 순서와 cold compile 때문에 실제 겹침이 있어도 전체 wall 차를 인과적 학습가속으로 채택하지 않는다. 두 새 런은 버전드 새 자료만 만들고 현재 v19~v23·원래 부모/체크포인트/결과101 원본을 변경하지 않는다.

### Stage3cW 품질 사후 감사 — 운영 안전과 답변 능력의 반례

C4는 좁은 SFT-val CE3.700334→3.571472로 개선됐지만, 같은 base full-val 2,929 crop에서3.600580→3.619024(**+0.018444 악화**)다. `PILOT_SAFETY_PASSED`의0.1nat 운영 문턱 안이라는 이유로 악화를 지우지 않는다. 부모 고정8문항은 채팅 시작 마커를 반복했고 자식 고정8문항도 모두80토큰 상한까지 갔다. 자식은 산수·지식에서 질문을 되풀이하고 논리 문항은 내용은 관련 있으나 요구한 yes/no 형식을 지키지 못해 **요구 정답과 형식 동시충족0/8**이다. 현재 legacy32는 `<|im_start|>`/종료 마커가8/7개의 분절토큰이고, chat32는 ID3/ID4 한 개다. 직렬화기는 assistant 머리를 한 번만 붙이므로 중복 머리 생성이 구현상의 직접 중복삽입임은 관찰되지 않았다. legacy 부모의 채팅 표지 미학습·작은78k토큰 SFT·EOS만 멈추는 추론 경로는 원인 후보이며 **어느 하나가 유일 원인이라는 증거는 없다**.

동일 4epoch 소형 학습을 다시 반복하지 않는다. chat32 부모와 기존 legacy의 계보·prompt/종료 제어, 의미 있는 고정 원답 평가를 별도 후속으로 설계하고, 새 A1/A2의 생산성 결과를 먼저 회수한다. 현재 Stage3f/g0/g 런처는 사용자가 check-only로 시도해 음성8을 남겼지만 통합·새 corpus·학생학습 **0**이다. A1Wb/A2Wb가 추후 성공해도 v22/v23 기존 SHA를 재해석해 원래 통합런처를 통과시키지 않고, 사용자 의미·자원 판단 후 새 단계로 별도 사전등록한다.

## 5. 판정 기준·사전등록 범위

| 관측 | 판정 |
|---|---|
| Stage0 원본 SHA/선별 수16 미달·공개 v3 정확 질문 누출 | `HOLD8` 또는 입력결함 `FAIL9`, 교사 시작 금지 |
| Stage1a 구조화 완성 <12/16·wall>1800s·GPU 여유 미달 | **형식/자원 음성** `exit8`; 출력이 있어도 전부 미검증 후보 |
| Stage1b 교사 실시간 출력 고유 유효쌍<8/16·teacher/학생 OOM·표본 free<2GiB | 기능/자원 음성 `exit8`, 업데이트0 또는 부분 이력을 정확히 기록 |
| 형식/독립 loss 마스크 위반, 원본/부모/tokenizer SHA·태그 충돌, 프로세스/계측 오류 | 도구 실패 `exit9`, 품질 음성으로 오독 금지 |
| Stage1b 2업데이트·유한 gradient·assistant-only 지도토큰>0·교사 동시 생성 관측 | **기능 PASS만**. 번역 진실성·실무 학습속도·대화능력·정식 `TRAIN_READY`는 `NOT_RUN` |
| Stage1c 부모/학생 같은 P10036·공개 3과제×512의 문항별 원본·paired 추적 | **사후 진단 완료**. 회귀·개선 문항과 오답률만; 교사 단독효과·전체 지능은 `NOT_DECIDED` |
| Stage2iWe 공개 deck SHA·권리/비보호 계보·실제 token admission 후 1 optimizer/128개 fresh | 기능 PASS만; 누락·권리 경계·미상 token API는 tool fail9, 고유 원천/자원 고갈은 유효 음성8 |
| Stage2iWf가 동일 공개 deck SHA의 We 1회 PASS 뒤 5 optimizer/640개 fresh·샤드 SHA·언어별 실처리토큰 기록 | 처리율/공존 기능 PASS만. 단일 모델 품질·P106 ACCEPT·formal TRAIN_READY는 절대 아님 |

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
| Stage2jW/Wb | 각각 ≤0.17h/≤0.08h hard wall | 이번 사용자 한정 GPT 직접 교사-only GPU 4+1요청, 학생·checkpoint0; 진단 원본 결과101에 별도 기록 |
| Stage2fWb | ≤0.5h hard wall | 사용자 full 교사 GPU, 기존 부분 raw29시도 참조+누락7문항만 생성; 학생0 |
| Stage2iWd | ≤1.5h hard wall | 사용자 full 교사+P076 학생, OASST1 원천의 **1 optimizer 기술 gate**, Stage2fWb PASS 선결·checkpoint0 |
| Stage2kW | 약0.1h CPU | 정확 공개 v3/OASST2와 지정 보호 사전/word/TXT **읽기 전용** 구조·SHA/계수; 모델·복사·출력 deck0 |
| Stage2kWb | ≤0.1h CPU | 공개 Aya Dataset/OASST2 job 예상10,528건만 별도 ignored HF 20MB 샤드로 새로 기록; 보호 사전 접근0·교사/학생/GPU0 |
| Stage2iWe | ≤2.0h GPU | 공개 전용 medium 1 optimizer·실제 token admission·P076 부모, 체크포인트0. Stage2kWb 10,528 job 생성·새 smoke PASS 선결 |
| Stage2iWf | ≤6.0h GPU | 동일 public deck SHA의 Stage2iWe 1회 PASS가 선결. 5 optimizer·640 신선후보, 체크포인트0 |
| Stage2iWg | ≤2.0h GPU | 새 공개원천 low1·계측수리 실물 gate. 구 OASST1 low1 반복 아님; 신규 v17·128 fresh·checkpoint0 |
| Stage2iWh | ≤6.0h GPU | Wg low1·동일 source/부모/교사 SHA·정상 monitor·실제128 적용 선결; 신규 v18·640 fresh·checkpoint0 |
| Stage3aWb | ⚙1.5h·hard2h GPU | 기존1.140/1.015×·KO1~2/4 음성 뒤 질문 언어당16·ctx6144/output4096 별도v26; 사용자 실물 전 속도·OOM NOT_RUN |
| Stage3bWb | ⚙1.0h·hard2h GPU | 기존 serial KO4/8·overlap0 음성 뒤 질문 언어당16·ctx6144/output4096 별도v27; 학생 partial최대32행·통합0 |
| Stage2W | `NOT_ESTIMABLE` | 승인 원천의 실제 유니크 지도토큰·교사 accepted sample 비용·동일평가 확인 후 산정 |

## 7. 실행 파일·사전 점검

- Stage1aW: `run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh`는 결과101의 재현명령과 Git 이력으로 보존 후 삭제. 사용자 번역16건·완결9/16, 문턱12 미달 exit8; v1 덮어쓰기 금지.
- Stage1bW: `run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh`는 결과101/ Git 이력 보존 후 삭제. 상류 미달 check-only 중단·학생학습0, 원시 exit9 분류 결함→후속 CPU HOLD8 수정.
- Stage1aWb/Wc: 두 완료 런처는 결과101·Git에서 복구 가능하며 삭제. Wb sandbox 차단으로 모델0, Wc 승인 GPU 경로4쌍×2팔 종료0·v2 기록; 학생학습0.
- Stage1dW: 완료 런처는 결과101·Git 보존 후 삭제. 교사 교정형3/3 형식 통과이나 새 수치오류1, 자동 학습수락0.
- Stage1fW: 사용자 실행·결과101 §10에서 교정형16/16 형식 PASS·답안 결함8을 회수했다. `run_P106B_Stage1fW_teacher_repair_full16-done.sh`는 재현명령과 Git 이력 보존 뒤 사용자 승인 삭제 조건을 별도로 판정한다.
- Stage1gW: 역사 SH는 결과101 §11에 재현명령과 원본을 보존하고 완료 표기로 전이한다. 사용자 실행8행 중 lint7/8로 사전 문턱 실패; 재실행은 같은 v5에 하지 않는다.
- Stage2a/b/c/d/gW: [결과101 §14~§17·§19](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 사용자 실제 로그로 CPU 계약·태그15/16·v7 한국어13/2·학생 오프라인2업데이트를 회수했다. Stage2e 공개 v3 job deck5,429개는 생성됐으나 교사 답/품질이 아니다. Stage2fW는 문항26 HTTP500·출력 manifest 부재로 **미완·exit9**이며 Stage2fWb 별도 보충이 필요하다.
- Stage2hW: 이번 지시의 명시적 단기 CPU+GPU 허용으로 교사-only 12요청을 직접 실측했다. v9 write-once 원본과 별도 runlog를 결과101에 회수한다. **학생 온라인 5회가 아니다.**
- Stage2iWa/Wb/Wc: [결과101 §20·§27~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 Wa는33요청/optimizer0 도구 사고, Wb none은5/5·52분 기술 완료, Wc medium은4/5·한국어365원천 소진 exit8로 분리한다. Wc의 canonical 형식 후보611 중 실제 학생 업데이트에 들어간 것은512다. 구 v10 원본 불변·같은 단계 재실행 금지. OASST1 B/C와 새 Aya/OASST2 공개 원천의 효과를 한 변수 비교로 오인하지 않는다.
- Stage2jW/Wb: 이번 사용자 한정 Codex 교사-only4+1요청의 별도 v11/v12 결과가 [결과101 §21~§22](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 있다. 교사 native parser의 문항26 HTTP500은 정확 PEG 불일치, bypass의 HTTP200은 길이 소진·중복 태그로 답안 불가다. 사용자 재실행 단계가 아니며 같은 출력 버전을 재사용하지 않는다.
- Stage2fWb/Stage2kW/Wb·Stage2iWd: [결과101 §23~§26](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 Stage2kW 읽기 전용87,361 job과 Stage2fWb 한영 형식 KO14/EN15을 보존한다. 2026-09-29 새 smoke43/0/0/0 뒤 Stage2kWb 공개 job10,528과 Stage2iWd low 동시 1 optimizer·약76.8분 완료, checkpoint/품질0. 실물 기술 경로는 열렸으나 교사 진실성·formal SFT는 아니다.
- Stage2iWe/Wf: We medium 첫실행은 sampler `TimeoutExpired` 미처리 뒤 사용자 Ctrl+C·optimizer0/후보123이었다. 같은날 로그 삭제 후 재실행은 output존재 check-only exit9였다([결과101 §29](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 사용자 지시로 medium 보류, We -done·재현 보존 후 삭제 판정, 미실행 Wf SH는 HOLD로 보존하며 모델 전 check-only8로 막는다.
- Stage2iWg/Wh: Wg는 사용자 9/29 기술1회 완료([결과101 §30](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)); 해당 SH는 명령4개와 Git 복구점을 남기고 삭제했다. Wh low5는 지금 [보존 SH](../run_P106B_Stage2iWh_online5_public_low-hold.sh)로 개명해 직접 실행도 HOLD8로 차단했다. 두 팔의 학습량을 합치거나 Wh를 이미 수행한 것으로 표기하지 않는다.
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

### Stage3 실행 파일 (모두 사용자 실행·새 smoke 선결)

- 역사 Stage3a/b/c0/c/d/e/f/g0/g 아홉 SH는 전부 사용자 9/30에 **착수된 이력**이다. 각각의 정확한 명령4개와 성공·음성·미실행 구분은 [결과101 §31·재현부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존했다. `-done`은 사용 시도 표지이지 A1/A2/통합의 과학적 성공 표지가 아니다.
- 다음 사용자 실행용: [A1 Stage3aWb 새 예산 ABBA](../run_P106B_Stage3aWb_parallel_teacher_budget_recovery.sh), [A2 Stage3bWb 새 예산 생산·소비](../run_P106B_Stage3bWb_teacher_student_overlap_recovery.sh). 둘 다 **새 smoke 선결·본런 미실행**이며 통합·실교육을 자동 재개하지 않는다.

§7 handoff 큐는 실제id·시간·조건부상태 정본이다.1개의update로4epoch완료를 보고하지 않으며300M 목표는 현재 코퍼스 부족·생산비용 때문에 별도 원천확장/품질 계획을 요구한다.

## 8. 한계·보호선

OASST2의 review/rank는 사실성 보증이 아니다. 교사 번역도 독립 정답이 아니므로 P106의 검증형 `ACCEPT` 원장을 이 실험으로 채우지 않는다. 출처 카드 Apache-2.0 표기는 개별 텍스트의 개인정보·권리 승인이 아니다. 자동 연락처/숫자 검사는 **명백한 경우만** 걸러 의미 왜곡 전부를 검출하지 않는다. 그래서 원문·교사가 실제 가르친 문구·선정/거부 상태를 버전드 데이터셋에 남기고 사후 분석한다. 사전 파일의 뜻풀이가 전부 존재해도 다의어 표준번호·출처/라이선스·용례 유형을 건너뛰지 않는다. 원칙적으로 GPT가 보호 `concept`/사전 원본을 HF에 복사하거나 학습·GPU를 대신 실행하지 않는다. 이번 사용자 지시에만 허용된 Stage2jW/Wb 교사-only 초소형 GPU 진단은 이 원칙의 **한정 예외**이며 학생·사전 원본을 건드리지 않았다. 성공해도 13유니크×2업데이트의 과적합·분산 때문에 Stage2 대조 없이 데이터 채택을 판정하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-27: 사용자 질문에 따라 ‘독립 정답 전수승인’이 일반 SFT의 필수조건이라는 과도한 전제를 철회하고, P106 검증형 `ACCEPT`와 P106B 자동 번역 `PSEUDO_UNVERIFIED`를 분리했다. 승인된 정확 `concept`와 사전 두 파일만 읽기 전용으로 구조·겹침을 확인했다. OASST2 Stage0 CPU 선별 자기시험/check-only에서 1326→잔존138·선정16을 확인했다. 교사 실제 번역·학생 학습·새 smoke는 `NOT_RUN`이다.
- 2026-09-27: 사용자 [결과101](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 새 smoke43/0/0/0 뒤 Stage1aW 교사16응답 중 완결9·미완결7, 실측 wall173.97초·총 생성10,429토큰을 회수했다. `12/16` 사전 문턱 미달은 §3이 경고한 형식 음성으로 유지한다. 당시 파서는 비정상 `finish_reason`을 하나로 뭉치고 사고/최종 부분출력·행별 사용량을 저장하지 않아 **절단 원인 귀속이 불가**하다. Stage1bW는 상류 실패 뒤 check-only에서 종료9로 잘못 분류했고 실제 교사+학생 학습은0회였다. 후속 코드는 같은 v1 문턱을 HOLD8로 고쳤지만 원본 로그는 수정하지 않는다. 새 설정의 재실행은 다른 단계·데이터 버전으로만 연다.
- 2026-09-27 후속: Stage1aWb는 기본 sandbox NVML 실패로 교사 적재0, Stage1aWc는 사용자 한정 허용 경로에서 4쌍 대응 cap768 0/4 대3072 3/4 완결을 확인했다. 사고문은 양쪽4/4 존재, 최종 문구는 큰 cap3/4에만 있었다. v2 raw는 불변이다. 직접 읽은 WebRTC 번역은 원문 API 오개념을 옮겼고, 교사 교정형 Stage1dW는 세 문항 JSON3/3을 냈으나 자기 `CORRECTED` 2건 중 하나가 GPT‑3 175B를 **175억**으로 새로 오기했다. [결과101 §9](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 외부 API/논문 근거 대조에 따라 그 행은 REJECT, WebRTC는 API 사실만 부분 확인, 수학50·20은 산술 확인이다. v3 원본·점검표를 별도 보존하고 자동 `ACCEPT`/학생학습0을 유지한다.
- 2026-09-28: 사용자 새 smoke43/0/0/0 뒤 Stage1fW full16 완결, 교사 자기 `CORRECTED`8/`PRESERVED`8. 직접 검토에서 새 결함8·추가검토4·잠정4라 자동 학습 채택0을 유지한다. 사용자 승인 A로 Stage1gW의 결함8만 프롬프트·진단기 response hook·최대3회 재시도에 연결했다. v5 출력은 새 버전·모델 사용자 실행 전 `NOT_RUN`이다.
- 2026-09-28 사용자 새 [smoke](../smoketest_logs/202609281223_smoke_cf99a59.txt)는 이전 `cf99a59` 트리의43팔·실패0·exit0 오류표지0·계측0이었다. [결과101 §14~§20](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 Stage2a/b CPU 계약, Stage2c 태그15/16·JSON14/16, Stage2d 한국어13+2행, Stage2f 문항26 HTTP500 미완, Stage2g 학생2업데이트/비패딩36,894, Stage2iWa 교사33응답·optimizer0/5를 구분했다. Stage2g CE 하락은 같은13행 반복 train 내 결과이지 val/대화 품질이 아니다.
- 2026-09-28 GPT 한정 직접 Stage2jW/Wb: 새 서버의 Stage2f 문항26에서 `peg-native format` HTTP500을 재현했고 입력817+max4096<ctx6144·free≈8.5GiB였다. parser bypass는 HTTP200이나 `length`4096·반복 태그로 불완결이어서 학생 target 금지. Stage2i 원 실패 입력은 교사-only 새 서버에서 HTTP200이므로 공통 원인을 단정하지 않는다. v8/v10 원형과 새 v11/v12 진단은 각각 불변이다.
- 2026-09-28 사용자 다원천 C안·초과길이 A안 선택: 기존 공개 v3 `oasst`는 OASST1이라는 계보 오류를 정정했다. 고정 OASST2 ready trees13,854 중 reviewed 영어 단일턴5,400/한국어5; 새 Stage2kW 읽기 전용 계약은 Aya Dataset 영어1,439개·OASST2 중복제외 영어3,824/한국어1개·사전 뜻풀이76,833 locator를 분리해 계수했다. 87,361 job은 답안/학습토큰이 아니다. 보호 원문/교사 변환 실행은 별도 정확 권리·파생 승인 기록 전 `HOLD`이고, 1200자 초과는 교사 실제 template 토큰 예산을 재어 DIRECT/압축 별도 child로 분기한다.
- 2026-09-28 사용자 반환: Stage2kW 독립 CPU 결과는 87,361 job/read-only, Stage2fWb는 old29+new8시도·case26 PEG500 2회에도 KO14/EN15로 사전 각12/16 형식 문턱을 통과했다. 이것은 학생 학습·한영5:5·교사 정답 PASS가 아니다. 새 코드/권리 분리 뒤 사용자 smoke는 별도 재실행이 필요하다.
- 2026-09-28 공식 정책 대조: 사전 별도 저장은 독립 공개원천과의 물리·계보 혼합을 막지만, 사전 예문/뜻풀이의 표현을 변형한 행의 권리나 모델 공개 시의 법적 판단을 자동 면제하지 않는다. Stage2kWb는 공개 source만 쓰고 보호 계열 전송/복사0; 사전 파생 별도 후보셋/개념만 재합성의 범위는 사용자 추가 선택과 검토에 따라 별도 구현한다.
- 2026-09-29 사용자 [smoke](../smoketest_logs/202609290441_smoke_b12060e.txt) 43/0/0/0과 [결과101 §25~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) 회수: 공개 전용 Stage2kWb job10,528·Stage2iWd low1/1·Wb none5/5 기술 기능을 확인했으나, Wc medium은 한국어365후보를 모두 써도 4/5에서 exit8이었다. Wc 형식 후보611 중 학생 optimizer에 실제 적용된 것은512, 남은99는 미적용 raw/canonical 후보로만 보존한다. none5의 비패딩141,422토큰과 medium4의100,408토큰은 300M/600M이 아니고 checkpoint/held-out 평가0이다. 장시간 서버 오류 tail에서 GDN 시작 줄이 밀린 결함은 계측 보강했지만 새 GPU 런 전에는 해당 팔 fusion 상태 `UNKNOWN`. 사용자 선택 A로 공개 Aya/OASST2 전용 Stage2iWe 1회→통과 시 Stage2iWf 5회만 준비했으며 현 E2E는 `NOT_RUN`이다.
- 2026-09-29 후속 [smoke](../smoketest_logs/202609291711_smoke_848dd6a.txt)는848dd6a 실행 당시43/0/0/0. We 첫실행의 계측 daemon timeout이 main에 전달되지 않은 **코드 결함**은 사용자 traceback과 exact v15 원형141/후보123·updates0으로 확인했다. ctx/출력상한이나 교사 품질 실패라고 단정하지 않는다. Ctrl+C/status와 sampleerrors 누락·후속 dataset output collision을 각각 수리/설명하고 medium은 보류했다. low 이미 실행했던 OASST1 Wd1 성공은 보존하며, 사용자 재선택 A로 새 공개원천·수리코드 Wg1→통과시Wh5를 별도 단계/버전으로 준비했다. 다음 가설은 계측 오류가 다시 발생하면 조용히 학습을 계속하지 않고 원본·partial을 남기며 fail9하는가이고 실물 결과 전 미확인이다.
- 2026-09-30 회수: 9/29 Wg low1은 새 source에서128답/1optimizer·원형196행·유효25,133대화토큰으로 완료됐다. sampler errors0와GDN latchtrue를 관측해 작은 기술 gate만 PASS로 옮겼다([결과101 §30](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 길이절단55건이 교사시간43.635%를 쓴 것은 남은 생산병목이다. 사용자 B,C4,A1+A2와 독립C4 뒤 통합1→실교육 승인에 따라 Stage3 9개SH/구현을 준비했으며 모델실행0. 별도 미실행Wh/Wf는 보존했다.
- 2026-09-30 2차 회수: 새 [smoke](../smoketest_logs/202609300046_smoke_f417544.txt)43/0/0/0 뒤 [결과101 §31](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 아홉 Stage3 시도를 분리했다. 예측한 A1 두 순서>1.05는 역순1.015로 **불성립**, 예측한 A2 실제 겹침은 KO4/8 문턱미달로 **미측정**이다. B2/B4 형식은 한영4/4로 예상보다 잘 되었지만 teacher 정답성은 여전히 별도다. C4는4pass·4optimizer를 완료하고 좁은SFT-val CE를 개선했으나 base full-val+0.018444 악화·고정답8/8 실패로 ~~운영 중단선 통과 뒤 바로 후속교육~~ 해석을 철회한다. 상류차단 f/g0/g는 실행 시도 로그만 있고 실교육0이다. 사용자 선택 A에 따라 토크나이저 계보·원답을 CPU 대조하고 A1Wb/A2Wb만 새v26/v27로 준비한다. 새 GPU 결과 전 통합 HOLD, Wh/Wf 미실행 두 파일은 `-hold`/큐 제외다.
