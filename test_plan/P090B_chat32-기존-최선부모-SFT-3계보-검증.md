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

### Stage0bW — 공개 v3 전수 무원문 마스크·split 선결, 정식 학습과 분리

[공개 preflight](../scripts/diag_p090b_public_preflight.py)를 [독립 SH](../run_P090B_Stage0bW_public_sft_preflight.sh)로 실행한다. SHA-pinned train/val·legacy tokenizer, source-ID/첫 질문 중복, 지도토큰 비율·빈 마스크와 3,154행의 assistant 본문(M3)·종료토큰(M4)을 **원문 출력 없이** 검사한다. Codex의 비보호 공개 v3 읽기 전용 관측은 train 2,996행(ko175/en2821)·val158행, split 겹침0·빈 마스크0·지도비율 train75.19%/val75.03%, M3/M4 누락 각각0이다. 직접 계산한 full-mask gate는 PASS지만 manifest의 tokenizer_mask 표기는 아직 NOT_RUN이고 contamination/source-quality도 NOT_RUN이므로 `TRAIN_READY=False`, pilot-only다. 이 단계의 exit0은 정식 SFT 승인 신호가 아니다.

이번 후속 자동 선별은 canonical train/val SHA와 각 행의 출처 revision·Apache-2.0 표기를 메타데이터끼리 대조해 `source_metadata_gate=PASS`(불일치0)였다. 공개 v3 3,154행의 한국어는 184행(**5.83%**), 멀티턴은 879행, URL 포함54행·이메일형 문자열 포함6행, 동일 assistant 답안 최대 반복4회다. 이 집계는 원문을 출력하지 않고 출처/언어별 결정론적 사람 검토 행 인덱스만 남긴다. **같은 생성 계보의 Apache-2.0 메타 일치는 외부 라이선스 원문이나 개별 대화의 권리·정확성·안전성을 증명하지 않으며** 사람 품질과 전체 오염은 여전히 `NOT_RUN`, 정식 학습 `TRAIN_READY=false`다.

### Stage0cW — 공개 한국어 공감형의 엄격 멀티턴 복원·legacy mask 선결

[고정 SHA read-only 진단](../scripts/diag_p090b_empathetic_contract.py)과 [사용자 SH](../run_P090B_Stage0cW_empathetic_multiturn_contract.sh)는 원천 26,662행 중 single 8,094는 제외하고 `multi_2` 3,812/3,812, `multi_3` 14,755/14,756행만 질문·답변 줄머리의 정확한 교대 순서로 canonical 역할을 복원했다. 원본 24,932번째 행 1건은 질문 마커가 줄머리에 없어 추측 복원을 거부했다. 복원 후보 18,567행은 legacy 32k에서 모두 1024 context 이하이고 assistant 지도마스크 빈 행 0, 지도비율 52.96%였다. 첫 질문 정규화 중복 1,775행은 source/tree 단위 split 전에 묶어야 한다. 원문 출력 없이 유형별 사람 QA 50행의 인덱스를 결정론적으로 남긴다. 구조는 `PARTIAL`(제외1), tokenizer mask는 `PASS`이나 카드 수준 Apache-2.0은 개별 권리 증명 아님, 사람 사실성·PII·오염은 `NOT_RUN`, 따라서 `TRAIN_READY=false`다.

### Stage0dW — OASST2 영어 다회전 번역 pilot 후보 선별

[고정 SHA read-only 진단](../scripts/diag_p090b_oasst2_translation_candidates.py)과 [사용자 SH](../run_P090B_Stage0dW_oasst2_translation_candidates.sh)는 OASST2 ready tree에서 review 통과·비합성·영어 role 교대의 best-rank 경로를 한 tree당 하나만 고른다. 이 정책에서 다회전 2,378개를 확인했고 기존 공개 v3 첫 질문 exact 겹침 888, legacy 32k 길이 1024 초과 336, OASST2 내부 첫 질문 중복 1개를 걸러 후보 1,153개가 남았다. 고정 해시 순위로 번역 pilot 200개·사람 원답안 검토 50개 tree 행 인덱스만 출력하며 원문·번역물·파일을 생성하지 않는다. 앞선 원천 감사의 다회전 2,377은 선별 정책이 달라 서로 같은 집합이라고 주장하지 않는다. 카드 Apache-2.0 표기는 개별 권리 검증이 아니며, 영어 후보가 생긴 것만으로 한국어 학습 `TRAIN_READY`가 되지 않는다. 원문·번역 병렬 보존, 숫자·고유명사·맥락·사실성·PII 사람 검토와 번역 후 tokenizer/mask/중복·평가 오염 검사는 사용자 후속 단계다.

### Stage1aW — B chat32 신규 어휘·분리 캐시 준비

[P075 어휘 생성](P075_토크나이저-어휘예산과-한국어-분절.md)의 32개 단일 ID를 [준비 SH](../run_P090B_Stage1aW_chat32_prepare.sh)로 사용자 실행한다. 기본 legacy 어휘·cache를 덮지 않고 `tok-ko-en-32768-chat32.json` 및 `ko-en_601000000_chat32` 별도 경로만 만든다. `prepare`는 기존·부분 chat32 cache의 계보·hash·symlink를 fail-closed 검사한다. 준비 직후 같은 공개 v3 canonical 행을 새 어휘로 전량 재인코딩하는 [길이 gate](../scripts/diag_p090b_chat32_sft_lengths.py)를 실행해 1024 context 초과가 0건인지 확인한다. 실패 시 Stage1bW를 자동 개방하지 않는다. 이는 HF/디스크 I/O를 쓰는 사용자 소유 단계이며 Codex가 실행하지 않는다.

### Stage1bW — B 새 300M 부모 사전학습

[사용자 실행 SH](../run_P090B_Stage1bW_chat32_parent_300M.sh)는 m100s10 dense/CLA2·seed1337·KD off·Muon RMS4, 2289×8×16×1024=300,023,808 token을 신규 어휘로 처음부터 학습한다. **2배 풀은 600,047,616 token 이상**이므로 600M이 아닌 601M exact cache를 사전등록한다. Stage1bW를 단독 선택해도 공개 v3 chat32 길이 gate를 다시 실행하고, 초과가 있으면 GPU 학습 전에 중단한다. 부모·캐시의 hash·lineage가 없으면 SFT trainer가 거절한다. 기존 A legacy 부모는 다른 tokenizer와 기존 부모 초기화·pool600M 계보이므로 A/B의 차이는 **전체 계보/시스템 비교**일 뿐 순수 tokenizer 효과가 아니다. 같은 raw 문서 byte·부모 초기화까지 맞춘 후속 대조 전에는 인과 귀속하지 않는다.

### Stage1cW — C 기존 최선 부모 선정, 아직 자료 선결

[동일 원답안 SH](../run_P090B_Stage1cW_best_parent_panel.sh)는 같은 legacy ko-en 어휘의 d14 300M·d14 600M·d16 1200M 세 체크포인트를 각자 preset·token 네임스페이스로 지정한다. [P100 평가기](../scripts/eval_p100_capability_panel.py)는 기존 3필드 입력을 유지하고 이 5필드 지정만 추가했으며 모델 없는 metadata-only preflight는 3/3 PASS했다. 실제 원답안·형식·한국어/영어 판단과 P097 Stage4의 공통 벤치 근거를 대조해 C 부모를 **SFT 전에** 고른다. 다른 학습토큰·풀·구조를 가진 세 모델의 상대 답변은 설명적 후보 선별이지 구조/토크나이저의 인과효과가 아니다. 단일 영어 full-val이나 파일 존재만으로 '최선'을 선언하지 않는다.


### Stage2W — 3갈래 SFT, 원천 적격성 뒤에만

동일한 공개 canonical train/val, source/tree 단위 분리, 사람 품질·PII·중복·평가 오염 검사를 통과한 corpus로 각 부모의 tokenizer에 맞춰 다시 encode한다. 동일 assistant target **원문 byte와 레코드/epoch**, batch·LR·optimizer·실제 지도토큰을 기록한다. A와 C는 parent만 다르게 legacy tokenizer에서 비교 가능하되 pretrain 길이·구조가 다르면 `DESCRIPTIVE_ONLY`다. B와 A는 tokenizer뿐 아니라 pretrain 계보 차이도 있으므로 matched 신규 부모를 갖추기 전 단일 tokenizer 효과로 귀속하지 않는다. 실제 답안·형식·한국어·영어·멀티턴·full-val 망각을 함께 본다. 현재 v3의 한국어 비중은 5.83%뿐이므로 한국어 멀티턴 정식 corpus로 자동 승격하지 않는다. [공개 원천 선별 감사](../docs/20260923_한영일-SFT-멀티턴-공개원천-선별과-확보-감사.md) §6의 한국어 공감형 엄격 복원 pilot과 OASST2 영어 tree의 사람검수 번역 pilot을 별도 계보로 준비한 뒤, 검수된 같은 canonical 원문을 A/B/C에 사용한다.

### Stage3W — 최종 SFT 계보 판정

Stage1cW에서 고른 C 부모와 A/B가 같은 공개 원문·평가 질문을 사용했는지 확인한 후, 한국어·영어 내용 정확성, 형식·멀티턴, 망각, 연산·상주를 각각 보고한다. M0 `d16_cla2_norecur_rms4_t1200`은 존재 후보이지 한국어 '최고' 확정이 아니다. B는 새 사전학습 계보까지 바뀌므로 A 대비 순수 tokenizer 효과로 귀속하지 않는다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| Stage0 A 마스크 누출·end 미지도·CE gradient 오류 | SFT gate FAIL, 학습 금지 |
| B chat32 어휘·601M cache·같은 tokenizer SHA가 checkpoint에 없음 | B NOT_READY, A/C와 품질 비교 금지 |
| Stage1b 신규 부모에 old init/KD·legacy cache가 섞임 | 설계 무효, train 시작 전에 중단 |
| chat32 재인코딩 공개 v3 중 1024 context 초과가 1건 이상 | 현재 동일 canonical B SFT gate 음성, 행 필터·동일자료 대조를 재설계 |
| 601M chat32 pool와 기존 600M legacy pool의 차이 | A/B 시스템 비교만, tokenizer 단독 효과 결론 금지 |
| 보호 held-out 오염 미검사·공개 원천 QA 미완 | 정식 학습 `TRAIN_READY=0`, pilot-only와 공식 결론 분리 |
| 세 갈래 생성 평가 | source·부모·tokenizer 계보를 남긴 같은 질문의 원답안·common-bpb만 비교 |

## 6. 비용

| 단계 | 예상 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU·비보호 tokenizer |
| Stage0bW | 약0.1h | 비보호 공개 HF/sft_ready 읽기 전용 CPU |
| Stage0cW 한국어 공감형 | 약0.1h | 비보호 공개 HF/sft_sources·legacy tokenizer 읽기 전용 CPU |
| Stage0dW OASST2 영어 후보 | 약0.1h | 비보호 공개 OASST2·v3·legacy tokenizer 읽기 전용 CPU |
| B Stage1aW 어휘/601M cache | ⚙1~3h, 신규 분리 디스크 약1.2GB 이상 | 사용자 HF/CPU/디스크 |
| B Stage1bW 부모 300.024M | ⚙2h(환경 의존), 16GiB 단일 GPU | 사용자 모델/GPU |
| Stage1cW C 공통 원답안 | ⚙0.3h | 사용자 GPU/모델, 새 출력 JSONL |
| 3 SFT 팔 | 원천 지도토큰 수·epoch 확인 뒤 산정 | 사용자 GPU/모델 |

## 7. 실행 파일

`run_P090B_Stage0W_three_lineage_sft_gate.sh`, `run_P090B_Stage0bW_public_sft_preflight.sh`, `run_P090B_Stage0cW_empathetic_multiturn_contract.sh`, `run_P090B_Stage0dW_oasst2_translation_candidates.sh`, `run_P090B_Stage1aW_chat32_prepare.sh`, `run_P090B_Stage1bW_chat32_parent_300M.sh`, `run_P090B_Stage1cW_best_parent_panel.sh`를 작성, 결과번호096의 단계별 별도 로그를 사용한다. Stage1a/1b는 WSL smoke PASS와 사용자 실행이 선결이며 출력 collision이면 중단한다. Stage2 SFT 학습 SH는 corpus `TRAIN_READY`, chat32 부모, C 부모 선정 뒤 만든다. 이 문서는 사용자에게 실험용 파일 작성 자체를 데이터 gate 통과로 오인시키지 않는다.

## 8. 한계

기존 32k ChatML에서 special marker는 다중 토큰이다. 신규 chat32 부모가 없으므로 3갈래 모델 성능 결과는 0건이다. 공개 HF 원천 확보는 사용권/사람 품질/평가 오염 PASS가 아니다. Codex는 SFT 학습·모델 평가를 대리 실행하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: 기존 독립 SFT trainer self-test와 legacy 실토크나이저 합성 mask PASS. 공개 v3 직접 preflight는 train/val 2996/158행·split 겹침0·빈 마스크0·M3/M4 누락0으로 full-mask PASS지만 manifest tokenizer-mask/contamination/사람 품질은 NOT_RUN, TRAIN_READY=False. chat32 prepare/train·checkpoint SHA 계보·새 어휘의 공개 v3 길이 gate 자기시험과 Stage1a/1b SH는 STATIC_ONLY; 실제 chat32 부모·C 원답안·SFT/품질 `NOT_RUN`. P100 per-model preset/token parser self-test와 세 기존 checkpoint/JSON metadata-only preflight는 PASS.

- 2026-09-24 막힘 재감사: `TRAIN_READY=False`는 정식 SFT 런처 실행·성과판정의 gate이지 A/B/C 계보 검사·trainer 코드 작성의 전면 중단 사유가 아니다. 공개 오염/사람 품질, B 부모 실제 학습, C 공통 원답안은 사용자 실행·검토로 남기되 GPT 소유 코딩 결손은 작업원장에서 진행 중으로 추적한다. 데이터 적격성과 부모 '최선'을 현재 미검증으로 유지한다.
- 2026-09-24: 비보호 공개 v3 3,154행을 고정 P100 한영 9문항의 base/QA prompt와 사용자 turn 단위 exact 공백·대소문자 정규화로 비교해 중복 0건(`panel_exact_gate=PASS`)을 읽기 전용 관측했다. 이것은 **해당 9문항의 정확 일치만** 배제하며 전체 benchmark/보호 held-out 오염 검사나 사람 품질 PASS가 아니다. manifest의 `contamination_gate`·`source_quality_gate`는 여전히 NOT_RUN, `train_ready=false`; Stage2 정식 학습 SH는 아직 만들지 않는다.

- 2026-09-24 후속: 독립 SFT trainer의 정식 실행은 이제 manifest의 `contamination_gate`·`tokenizer_mask_gate`·`source_quality_gate` **세 항목 모두 PASS**가 아니면 fail-closed한다. `--pilot-only`에서만 HOLD를 명시한 채 허용하고, 결과 JSON에 세 gate·부모 step·n_layers/dim/ffn_dim/E/CLA/타잉/어휘 구조를 남긴다. 합성 self-test PASS. 현재 공개 v3 manifest는 contamination/tokenizer-mask NOT_RUN이고 사람 품질 승인도 없으므로 정식 SFT `TRAIN_READY=false`; A/B/C 실제 SFT·성능은 `NOT_RUN`.

- 2026-09-24 후속: 기존 Stage0b 공개 preflight에 출처/license/revision·언어비·멀티턴·URL/이메일·답안 반복 집계와 사람 검토 행 인덱스를 원문 없이 추가했다. 합성 self-test 및 공개 v3 read-only 실행 PASS: 출처 불일치0, 한국어184/3154=5.83%, 멀티턴879, URL54, 이메일형6, 답안 최대 반복4. `source_metadata_gate=PASS`는 사람이 판단할 `source_quality_gate=NOT_RUN`을 대체하지 않으며 formal SFT는 계속 HOLD다.

- 2026-09-24 상태 재감사: 공개 한국어 공감형 원천 고정 SHA에서 multi_2 3812/3812, multi_3 14755/14756 구조 복원(24932번 마커 이상 1건 제외), legacy 32k 1024 초과0·빈 지도마스크0·지도비율52.96%, 첫 질문 중복1775를 읽기 전용 확인했다. 사람 QA 표본 각50행 인덱스만 출력한다. 실제 원문 품질·PII·평가 오염·라이선스 개별 권리 `NOT_RUN`, canonical train/val 파일 생성0·학습0이므로 GPT 선결과 사용자 E2E를 분리한다.

- 2026-09-24 상태 재감사: 고정 OASST2 영어 ready tree의 review 통과·비합성 best-rank 다회전 2378개에서 기존 공개 v3 첫 질문 exact 겹침888, legacy 1024 초과336, 내부 첫 질문 중복1을 제외해 영어 후보1153개를 읽기 전용 확인했다. 번역 pilot200·사람 검토50 행 인덱스만 고정했고 번역·외부 송신·새 파일 작성0. 원문 사실성·PII·개별 권리·번역 품질·한국어 학습 적격은 `NOT_RUN`이며 이후 결과가 도착하면 새 WIP 항목에서 corpus 구성과 세 계보 대조를 재개한다.
