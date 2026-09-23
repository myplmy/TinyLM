# P090B — 기존 32k·chat32·최선 부모 SFT 세 계보 검증

> 사용자 2026-09-24 추가 선택: 두 토크나이저 계보와 기존 최고 성능 모델 init까지 세 갈래를 비교한다. [P090](P090_SFT-경로.md)의 기존 역사 절을 고치지 않는 별도 suffix 계획. 사용자 실행 전까지 SFT 학습·GPU·보호 held-out 평가는 `NOT_RUN`이다.

## 1. 왜

현재 [tinylm/chat](../tinylm/chat/serialize.py)의 canonical ChatML 양식과 [assistant-only loader](../tinylm/data/sft.py)는 있다. [독립 SFT trainer](../scripts/train_sft_p090.py)는 기존 32k 토크나이저와 부모 checkpoint에서만 학습한다. 실제 기존 어휘의 `<|im_start|>`·`<|im_end|>` 단일 ID는 없고, 별도 chat32 파일/부모는 아직 없다. 새 tokenizer를 예전 checkpoint에 바로 끼우면 token ID 의미가 달라 무효다.

## 2. 질문

| # | 질문 | 비교 가능한 관찰 |
|---|---|---|
| Q1 | A 기존 32k+ChatML 분절 토큰으로 SFT mask/학습이 안정적인가 | 한 부모·동일 공개 canonical 자료와 생성/망각 |
| Q2 | B chat32 단일-ID 어휘의 새 부모가 A보다 실제 형식·속도·품질을 개선하나 | 같은 원문 byte 평가, matched pretrain budget/구조/데이터 |
| Q3 | C 최선 기존 부모의 초기화가 A에 비해 이득인가 | 같은 legacy tokenizer·같은 SFT 자료·채점, 부모 차이 명시 |

## 3. 예측

A는 tokenization overhead가 있지만 지금 기능 gate를 통과할 수 있다. B는 ChatML 표지 비용을 줄여도 새 pretrain 부모·토크나이저 비용과 품질 대가가 생길 수 있다. C의 M0 1.2B 영어 full-val만으로 한국어 대화능력 우열을 정할 수 없다. 현재 C는 **후보 존재·선정 미완**이다.

## 4. 단계 설계

### Stage0W — 현재 자산·ChatML/mask 기능 gate

[세 계보 점검](../scripts/diag_p090b_three_lineages.py), [마스크 진단](../scripts/diag_sft_mask.py), [SFT 독립 trainer 자기시험](../scripts/train_sft_p090.py)을 [SH](../run_P090B_Stage0W_three_lineage_sft_gate.sh)로 묶는다. 합성 대화4종에서 prompt 지도0·assistant end 포함·다회전 turn 순서·CE/gradient를 확인한다. 보호 corpus·모델·GPU는 쓰지 않는다. 지금 관찰: A 토크나이저/부모 파일 있음, B chat32 토크나이저 없음, C M0 후보 파일은 있으나 '최선' 선정 미완.

### Stage1W — B chat32 신규 부모와 C 기존 부모 선정, 선결 미완

[P075 어휘 생성](P075_토크나이저-어휘예산과-한국어-분절.md)의 신규 tokenizer를 별도 이름으로 만들고 단일 ID 32개를 검증한다. 그 tokenizer로 같은 구조·원문 pool·약300M draw의 **신규 사전학습 부모**를 사용자 실행해야 한다. 예전 checkpoint를 단순 strict=False로 읽거나 embedding row를 같은 ID라고 복사하지 않는다. 이 단계를 대체할 embedding mapping은 별도 함수·초기 동등성 gate가 필요하다. 이번에 신규 부모 학습 SH는 만들지 않는다.
같은 단계에서 P100 원답안 panel·P097 Stage4 공통평가의 동일 질문·토크나이저·언어별 결과를 대조해 C 부모를 **SFT 전에** 확정한다. 단일 영어 full-val이나 checkpoint 파일 존재만으로 '최선'을 선언하지 않는다. 후보별 구조·pretrain 토큰·평가 경로가 다르면 C와 A의 비교는 설명적 관찰로 제한한다.


### Stage2W — 3갈래 SFT, 원천 적격성 뒤에만

동일한 공개 canonical train/val, source/tree 단위 분리, 사람 품질·PII·중복·평가 오염 검사를 통과한 corpus로 각 부모의 tokenizer에 맞춰 다시 encode한다. 동일 assistant target **원문 byte와 레코드/epoch**, batch·LR·optimizer·실제 지도토큰을 기록한다. A와 C는 parent만 다르게 legacy tokenizer에서 비교 가능하되 pretrain 길이·구조가 다르면 `DESCRIPTIVE_ONLY`다. B와 A는 tokenizer뿐 아니라 pretrain 계보 차이도 있으므로 matched 신규 부모를 갖추기 전 단일 tokenizer 효과로 귀속하지 않는다. 실제 답안·형식·한국어·영어·멀티턴·full-val 망각을 함께 본다.

### Stage3W — 최종 SFT 계보 판정

Stage1W에서 고른 C 부모와 A/B가 같은 공개 원문·평가 질문을 사용했는지 확인한 후, 한국어·영어 내용 정확성, 형식·멀티턴, 망각, 연산·상주를 각각 보고한다. M0 `d16_cla2_norecur_rms4_t1200`은 존재 후보이지 한국어 '최고' 확정이 아니다. B는 새 사전학습 계보까지 바뀌므로 A 대비 순수 tokenizer 효과로 귀속하지 않는다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| Stage0 A 마스크 누출·end 미지도·CE gradient 오류 | SFT gate FAIL, 학습 금지 |
| B chat32 어휘 또는 같은 ID의 새 부모 없음 | B NOT_READY, A/C와 품질 비교 금지 |
| 보호 held-out 오염 미검사·공개 원천 QA 미완 | 정식 학습 `TRAIN_READY=0`, pilot-only와 공식 결론 분리 |
| 세 갈래 생성 평가 | source·부모·tokenizer 계보를 남긴 같은 질문의 원답안·common-bpb만 비교 |

## 6. 비용

| 단계 | 예상 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU·비보호 tokenizer |
| B 신규 어휘/부모 | 어휘/300M 학습 별도 산정 | 사용자 데이터·GPU |
| 3 SFT 팔 | 원천 지도토큰 수·epoch 확인 뒤 산정 | 사용자 GPU/모델 |

## 7. 실행 파일

`run_P090B_Stage0W_three_lineage_sft_gate.sh`만 작성, 결과번호096. Stage2 학습 SH는 corpus `TRAIN_READY`, chat32 부모, C 부모 선정 뒤 만든다. 이 문서는 사용자에게 실험용 파일 작성 자체를 데이터 gate 통과로 오인시키지 않는다.

## 8. 한계

기존 32k ChatML에서 special marker는 다중 토큰이다. 신규 chat32 부모가 없으므로 3갈래 모델 성능 결과는 0건이다. 공개 HF 원천 확보는 사용권/사람 품질/평가 오염 PASS가 아니다. Codex는 SFT 학습·모델 평가를 대리 실행하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: 기존 독립 SFT trainer self-test와 legacy 실토크나이저 합성 mask PASS. 세 계보 인벤토리 A 존재/B NOT_READY/C 후보 존재·선정 미완. 실제 SFT/품질 `NOT_RUN`.
