# 실험계획 P090 — **SFT 경로를 연다**

> **작성 2026-09-08** · 제안서 [`20260907_SFT-경로를-연다.md`](../proposal/done/20260907_SFT-경로를-연다-approved.md)
> ★**승인 2026-09-08**(사용자 지시 3C). 사용자가 계획서에 담으라고 한 것 다섯을
> §1(왜 지능이 오르나) · §3(선결) · §4(데이터) · §5(벤치) · §9(성과가 없어도 유지할 가치)로 옮겼다.
> **2026-09-23 상태 정정:** §3~4의 “loader/data 없음”은 당시 설계 시점 기록이며
> §10에서 loader와 과거 소규모 corpus를 갱신했다. 현재 실제 ko-en tokenizer에는
> ChatML 단일 ID가 없고 기본 학습 trainer에는 SFT 배치가 연결돼 있지 않다. §11은 정적 준비, §12는 공개 자료 확보와 독립 SFT 진입점의 최신 판정이다.


---

## 1. ★★왜 SFT 가 지능을 올리나 — **무엇을 올리고 무엇을 못 올리나**

★**먼저 정직하게**: 🚫**SFT 는 모델이 모르는 사실을 가르치지 않는다.**
6,000 레코드는 우리 사전학습 300M 토큰의 ⚙**0.002%** 다. **지식 총량은 사실상 불변**이다.

★**그럼 무엇이 오르나 — 우리 실측이 정확히 그 자리를 가리킨다**(결과 074 §22 · 085 계열):

| 관찰 | 숫자 |
|---|---|
| ★**정답CE 는 맞는데 argmax 가 어긋난다** | 9쌍 → 이제 **5/5 · 4/4 · 3/3** 로 반복 재현 |
| ★`d16` 이 `arc_easy` 정답CE 를 **t 21.8** 로 이기면서 정확도는 **z −0.58** | 결과 074 §22 |
| ★**같은 5,197 문항에서 CE 는 13σ, 정확도는 0.03σ** | 🚫**검정력 문제가 아니다** |

★★**이 분리의 뜻**: 모델은 **정답에 높은 확률을 주고 있다.** 그런데
**후보들 사이의 상대 순위**가 안 잡힌다. 그것은 **지식이 아니라 출력 형식·정합의 문제**다.

★**SFT 가 올리는 것 셋**:

| # | 무엇 | 왜 우리 모델에 없나 |
|---|---|---|
| **1** | ★**"질문에 답한다" 는 형식** | 우리는 **SFT 를 한 번도 안 했다**. 생성 과제 점수가 0 인 것이 정상이다 |
| **2** | ★**후보 사이의 판별** | 대비 학습(`rejected`)이 **한 번도 없었다**. 사전학습은 *"다음 토큰"* 만 시킨다 |
| **3** | ★**답의 길이·형태를 문항에 맞추는 것** | held-out 의 `길이정규acc` 가 `우도acc` 보다 **낮다**(37.7% vs 33.0%) = 길이 통제가 안 된다 |

🚫**올리지 못하는 것**: 새 지식 · 긴 추론 · 계산.
→ ★**따라서 이 계획의 성공 지표는 held-out 정확도이지 full-val 이 아니다.**

---

## 2. 질문

| # | 물음 | 사전등록 문턱 |
|---|---|---|
| **Q1** | ★assistant-only 손실 마스크가 **정말 prompt 를 안 학습하나** | prompt 토큰의 손실 기여 **정확히 0** |
| **Q2** | SFT 가 **held-out 정확도**를 올리나 | McNemar z ≥ 2(필요 문항 **97**, 보유 300 — ✅검정력 있다) |
| **Q3** | ★SFT 가 **full-val 을 얼마나 망가뜨리나**(망각) | +0.05 이내면 수용 |
| **Q4** | 대비 학습(`rejected`)이 **추가로 버나** | Q2 문턱과 같다 |

---

## 3. ★선결 — **무엇이 있고 무엇이 없나** (사용자 물음)

| 조각 | 상태 |
|---|---|
| 채팅 직렬화기 · canonical 형식 | ✅**있다** — `tinylm/chat/`(직렬화기 4종 · 예약 슬롯 32) |
| 한국어 4지선다 채점 경로 | ✅**있다** — `eval_bench_suite --task stage1_heldout`(fetcher 가 D1/D6 ≠ 0 이면 거절) |
| 우도 채점(PMI·길이정규) | ✅**있다** |
| ★**assistant-only 손실 마스크 loader** | 🚫**없다** — ★**이것 하나가 셋을 못 잇게 하고 있다** |
| ★**SFT 학습 데이터** | 🚫**없다** — §4 |
| 대비 손실(DPO/rejected) | 🚫없다 — 단계4 에서 필요하면 |

★★**즉 선결은 코드 한 조각과 데이터 한 벌**이고, 코드 쪽은 ⚙**0.4h** 다.

---

## 4. ★데이터 — **별도 마련이 필요하다** (사용자 물음)

### 4.1 기존 데이터셋 실사 (2026-09-08)

| 자산 | 규모 | SFT 로 쓸 수 있나 |
|---|---:|---|
| `stage1_dataset/train` | 900 레코드 | 🚫**아니다** — `text` 서술문뿐 |
| `stage1_dataset/train_v2` | 900 + `paraphrases`(2) + `near_negatives`(3) | 🚫**직접은 아니다.** ✅**`rejected` 재료로는 최적** |
| `stage1_highdensity_dataset/train` | **227파일 · 34,000 레코드 · 2,586,544자**(⚙1.0~1.7M 토큰) | 🚫**아니다** — ✅**계속 사전학습에는 바로 된다** |
| `held-out_v2.7` | 300문항 (`prompt`·`answer`·`candidates`·`correct_index`) | 🚫🚫**절대 아니다 — 채점지다** |

★★**결론: SFT 용 데이터는 별도로 만들어야 한다.** 🚫**Claude 가 만들지 않는다**(사용자 지시 7B) —
**데이터셋 작성 LLM 에 줄 프롬프트**를
[`review_request/20260908_SFT용-데이터셋-생성-요청-프롬프트.md`](../review_request/20260908_SFT용-데이터셋-생성-요청-프롬프트.md)
에 만들어 두었다. **6,000 레코드 · `instruction`/`output`/`rejected` 스키마.**

### 4.2 ⚠️★가장 큰 위험 — **held-out 오염**

held-out 300문항의 주어 **214개 중 142개**가 고밀도 train 의 `concepts`(40,948개)에 이미 있다.
**설계대로**다(`seen_concept_control` 37문항이 그 자리). 🚫**그러나 SFT 를 같은 개념 풀에서
생성하면 `unseen_concept` 113문항이 무효**가 되고, 그러면
★**정확도를 가를 검정력이 있는 유일한 과제**를 잃는다(필요 문항 97 vs `arc_easy` 7,458).

✅**방어 둘**: ①생성 프롬프트의 제외 규칙 7개 ②받은 뒤 **n-gram 오염 재검사**(단계0b).

---

## 5. ★벤치마크 (사용자 물음)

| 과제 | 왜 | 검정력 |
|---|---|---|
| ★★**`stage1_heldout` v2.7**(한국어 300) | **주 지표.** SFT 가 고치려는 것이 정확히 이 축이다 | ✅**필요 97 / 보유 300** |
| `arc_easy`(2,376) | 영문 전이 | 🚫필요 7,458 — **보조** |
| `hellaswag`(5,000) | 영문 상식 | 🚫필요 7,963 — **보조** |
| ★**full-val `paired_eval`** | ★**망각 감시**(Q3) | ✅자 0.0024 |
| 공통 원문 bpb | 독립 코퍼스 망각 | ✅자 0.0038 |

⚠️★**생성 과제(gsm8k·ifeval·humaneval)는 넣지 않는다** — 100M base 에서 0 이 정상이고,
**SFT 6,000 레코드로 0 이 아니게 되지 않는다.** 🚫**넣으면 0 을 세 번 더 확인할 뿐이다.**

---

## 6. 단계

| 단계 | 무엇 | ⚙ | 학습 | 선결 |
|---|---|---:|---:|---|
| ★**단계0a** | **마스크 진단** — 합성 데이터로 `prompt 기여 == 0` 확인 | **0.2h** | 0 | 단계1 구현 |
| ★**단계0b** | **오염 재검사** — 받은 SFT jsonl ↔ held-out 300문항 n-gram | **0.1h** | 0 | 데이터 도착 |
| ★**단계1** | `assistant-only` 마스크 loader 구현 + 스모크 팔 | **0.4h**(구현) | 0 | — |
| ★**단계2** | ★**SFT 1런** — `d14_cla2_norecur_muon15` 위에 6,000 레코드 3 epoch | **1.0h** | 1 | 단계0a·0b |
| ★**단계3** | 채점 — held-out · arc_easy · full-val 망각 | **0.6h** | 0 | 단계2 |
| 단계4 | 대비 학습(`rejected`) 추가 | 1.2h | 1 | ⏸단계3 이 Q2 를 통과할 때만 |
| 단계5 | ⏸**계속 사전학습 팔** — 고밀도 34,000 레코드를 사전학습에 얹는다 | 2.5h | 1 | ⏸**별개 축**(§8) |

★**합계 ⚙2.3h**(단계0a~3) · **구현 0.4h.**

---

## 7. ★사전등록 예측

| # | 예측 | 반증되면 |
|---|---|---|
| **P1** | 마스크 진단에서 prompt 기여 **정확히 0** | 🚫**구현 결함. 여기서 멈춘다** |
| **P2** | held-out `우도acc` **+3 ~ +10pp** | 0 이하면 *"형식이 아니라 지식 문제"* 로 판정이 뒤집힌다 |
| **P3** | ★**`길이정규acc` 가 `우도acc` 보다 더 오른다** | 길이 통제가 SFT 로 안 고쳐진다는 뜻 |
| **P4** | full-val 망각 **+0.02 ~ +0.08** | +0.15 초과면 SFT 비율·LR 을 다시 짠다 |
| **P5** | `arc_easy` 는 **안 움직인다**(한국어 SFT · 영문 과제) | 움직이면 **형식 이득이 언어를 넘는다** = 더 큰 발견 |

---

## 8. 🚫이 계획이 하지 않는 것

- **RLHF·DPO 전체** — 단계4 는 **`rejected` 한 개짜리 대비 손실**이지 선호 최적화 파이프라인이 아니다.
- **계속 사전학습**(단계5) — ⚠️★**이것은 SFT 가 아니라 데이터 축**이다.
  고밀도 34,000 레코드는 **한국어 유니크 토큰을 ⚙1.0~1.7M 늘린다** — 우리 풀 600M 의 ⚙0.2~0.3% 다.
  🚫**작다.** **P088(토큰 축)에 붙이는 것이 맞고 여기서는 자리만 잡아 둔다.**
- **채팅 템플릿 설계 재검토** — `tinylm/chat/` 이 이미 있다. 🚫**바꾸지 않는다.**

---

## 9. ★★성과가 없어도 이 경로를 유지할 가치가 있나 (사용자 물음)

★**있다. 이유 넷을 숫자로 적는다.**

| # | 이유 | 숫자 |
|---|---|---|
| **1** | ★**배포 상주를 한 바이트도 안 쓴다** | SFT 어댑터 없이 **전체 미세조정**이므로 파라미터 수 불변 = **Δ상주 0** |
| **2** | ★**우리에게 검정력 있는 유일한 지능 과제를 쓰는 유일한 축**이다 | held-out 필요 문항 **97 / 보유 300**. 메모리 축 실험은 이 과제를 **못 움직인다**(같은 계열 z ≤ 1.2) |
| **3** | ★**음성 결과도 판정이다** — P2 가 0 이하면 *"우리 문제는 형식이 아니라 지식"* 이 **확정**된다. 그러면 **토큰 축·데이터 축이 유일한 길**이라는 뜻이고, 그것은 큰 정보다 | ⚙2.3h 로 산다 |
| **4** | ★**배포에 필요하다** — 어떤 형태로 쓰이든 최종 모델은 지시를 따라야 한다. **언젠가 반드시 해야 하는 일**이고, 지금 하면 **파이프라인 결함을 싸게 발견**한다 | 구현 0.4h |

⚠️★**단 한 가지 조건**: **held-out 오염이 확인되면 즉시 멈춘다**(단계0b).
🚫**오염된 채로 진행하면 이 경로가 우리 유일한 계기를 부순다** — 이득보다 손해가 크다.

---

## 10. ✅★★단계1 완료 — **마스크 loader · 스모크 팔 · 채점 경로 셋 다 생겼다** (2026-09-10(2차))

> 사용자 지시 3: *"`assistant-only` 마스크 loader 및 마스크의 스모크 팔,
> SFT 채점 경로(`--task sft_fresh_eval`) 구현."*

### 10.1 ✅선결 표 갱신

| 조각 | 종전 | ★지금 |
|---|---|---|
| ★**assistant-only 손실 마스크 loader** | 🚫없다 | ✅**`tinylm/data/sft.py`** |
| ★**마스크 스모크 팔** | 🚫없다 | ✅**`scripts/diag_sft_mask.py`** + 팔 **[21d]** + 진단계약 한 줄 |
| ★**SFT 채점 경로** | 🚫없다 | ✅**`eval_bench_suite --task sft_fresh_eval`** + fetcher |
| ★**SFT 학습 데이터** | 🚫없다 | ⚠️**왔다**(fresh v1) — 🚫**권장의 0.7%**(감사 2026-09-10) |

### 10.2 ★규약 — **문자 구간에서 토큰 구간으로**

`tinylm.chat.serialize.loss_spans()` 가 **문자 구간**을 주고(토크나이저를 안 부른다)
`sft.py` 가 `offsets` 로 토큰에 매핑한다. ★**완전 포함만** 센다 —
경계에 걸친 토큰을 넣으면 **입력의 마지막 글자**가 지도 토큰이 되고
그것은 *"질문의 끝을 예측하라"* 는 신호다.

★**밀기는 한 곳에서만** 한다 — loader 는 **안 민** `labels` 를 주고
`sft_targets()` 가 `x = ids[:-1]`·`y = labels[1:]` 로 자른다(`trainer.py` 와 같은 규약).

### 10.3 ★★실측 — **채팅 템플릿이 토큰을 절반 더 먹는다**

`sft_fresh_v1_train_1000` · 실토크나이저(`ko-en` 32,768):

| | 값 |
|---|---:|
| 감사가 잰 **본문** 토큰(2026-09-10) | 74,415 |
| ★**ChatML 로 감싼 뒤 총 토큰** | ★**111,415** |
| → **템플릿 오버헤드** | ★**+37,000 = +49.7%** |
| ★**지도 토큰**(assistant + `<\|im_end\|>`) | ★**29,272** |
| 지도 비율 | **26.3%** |
| 최장 레코드 | 164 토큰 |
| 빈 마스크 · M3 · M4 · M5 위반 | **0 / 0 / 0 / 0** |

🚫★★**오버헤드 49.7% 는 결함이 아니라 예고된 값**이다 — 우리 어휘에 `<|im_start|>`·`<|im_end|>` 가
**아직 없어서** 경계 하나가 5~8토큰으로 쪼개진다(`docs/…채팅템플릿…` §9).
★**P075 단계1(어휘 재학습 + 예약 슬롯 32)이 그것을 한 토큰으로 만든다.**
→ ⚠️**SFT 규모를 토큰으로 요청할 때 이 오버헤드를 함께 적는다**(요청서 부록 C 갱신 대상).

### 10.4 ★채점 경로 — **규칙이 데이터에 있다**

`--task sft_fresh_eval` 은 생성한 뒤 `meta.grading` 이 들고 온 규약으로 채점한다.
🚫**도구가 모드를 추측하지 않는다.**

| `scoring_mode` | 문항 | 통과 조건 |
|---|---:|---|
| `normalized_exact` | 60 | 정규화 후 정답 문자열 포함 · 금지어 없음 |
| `required_elements` | 60 | 필수 전부 · 금지 없음 |
| `choice_and_required_elements` | 60 | 위 + **다른 선택지가 함께 나오지 않는다** |
| `required_elements_and_format` | 60 | 위 + `format_constraints`(문장 수) |
| ★`diagnostic_required_elements` | 60 | ★**미채점**(`ranking_eligible: false`) — 진단 전용 |

→ ★**무인 채점 240 / 300 = 80%.** ⚠️요청서가 예고한 **90%** 에 못 미치는데
원인은 **T1(우도 4지선다)이 0건**이기 때문이다(감사 2026-09-10) — v2 요청의 핵심이 그것이다.

🚫★**`normalized_exact` 를 문자열 완전일치로 재지 않는다** — gold 가 *"미리내통이다."* 처럼
조사·마침표를 달고 있어 완전일치는 **정답을 오답으로 만든다**. ★*"정답을 포함하고 금지어가 없다"* 로 잰다.
⚠️**그 사실을 결과에 적는다** — 공식 EM 이 아니다.

### 10.5 ✅검증 — **28/28**

| 무엇 | 결과 |
|---|---|
| 어댑터(프롬프트가 assistant 머리로 끝나고 **정답이 안 들어 있다**) | ✅ |
| 다섯 모드 × (정답 통과 · 빈 답 실패 · 금지어 실패) | ✅ **12/12** |
| `diagnostic_*` 이 **미채점** | ✅ |
| 모르는 모드 · 규약 없음 → **미채점**(실패 아님) | ✅ |
| 정규화(NFKC · 공백 축약) · 문장 수 제약 | ✅ |
| 마스크(본문 덮음 · 입력 누출 0 · 경계 포함 · 밀기 · labels 값) | ✅ **6/6** |
| 스모크 팔 [21d] 를 CPU 로 직접 실행 | ✅ **exit 0**(합성 4종 · 실코퍼스 1,000 둘 다) |

### 10.6 🚫이 단계가 하지 않는 것

- 🚫**학습을 안 돌린다.** 단계2 는 여전히 **데이터 규모가 선결**이다(현재 권장의 0.7%).
- 🚫**배치를 안 만들었다**(R22) — 지금 돌려도 **1 epoch 이 5스텝**이라 읽을 수가 없다.
- 🚫**`train_thinking=False` 를 안 쓴다** — `loss_spans` 가 블록 분할을 아직 안 한다.
- ⚠️**`--task sft_fresh_eval` 의 첫 채점은 0 이 정상**이다(base LM). ★**그것을 확인하는 것이 첫 런의 목적**이고
  정답CE 는 0 이어도 **연속값이라 서열을 만든다**(결과 050 의 수법).

## 11. 2026-09-23 공개 SFT·멀티턴 준비 — 정적 선결만 진행

### 11.1 현재 코드·실물 경계

- 실제 비보호 `data_cache/tok-ko-en-32768.json`을 모델 없이 조회했다.
  vocab 32,768, `<|im_start|>`와 `<|im_end|>`의 `token_to_id`는 둘 다
  `None`이었다. `chat/tokens.py`의 예약 이름 32개와 실제 어휘 할당은 다르다.
- `tinylm/data/sft.py`는 canonical 다회전 대화의 assistant-only mask와
  한 칸 이동 규약을 구현한다. `diag_sft_mask.py`의 과거 CPU 계약을 재사용하되,
  이 턴에는 보호 corpus를 열지 않았다. 기본 `train()`은 SFT corpus를
  읽지 않고 사전학습 `Loader`를 호출하므로 SFT 학습 자체는 `NOT_RUN`이다.
- CE 청킹이 `-100` label을 거부하던 선결은 유효 target 분모로 수정했다.
  CPU에서 masked/unmasked CE와 gradient를 PyTorch 기준과 비교해 통과했다.
- `build_chat_tokenizer`는 기존 tokenizer 파일을 덮지 않고 별도
  `tok-{name}-{vocab}-chat32.json`으로 32개 예약 슬롯을 단일 ID로 훈련한다.
  합성 토큰 fixture만 PASS했으며 실제 코퍼스 훈련·모델 재학습은 `NOT_RUN`.
  **새 tokenizer의 ID를 기존 checkpoint에 대입하면 안 된다.**

### 11.2 데이터 출처와 품질 게이트

사용자는 Apache 등 공개 라이선스가 명확한 소스를 `HF/` 별도 경로에
확보하는 방향을 승인했다. 첫 후보는 pinned
`CohereLabs/aya_dataset@f9ea04583f02a8f86404ff6c58bf75fe637df8a2`
(Apache-2.0, 한국어/영어 단일턴)과
`OpenAssistant/oasst1@fdf72ae0827c1cda404aff25b6603abec9e3399b`
(Apache-2.0, 다회전 tree)다. 공식 카드:
[Aya](https://huggingface.co/datasets/CohereLabs/aya_dataset),
[OASST1](https://huggingface.co/datasets/OpenAssistant/oasst1).

`scripts/prepare_public_sft.py`는 원본을 `HF/sft_sources`에만 내려받고,
Aya original annotation·OASST ready tree에서 한/영 canonical을 만들어
`HF/sft_ready`에 이름 충돌 없이 저장한다. OASST는 tree당 하나의
best-rank 경로만 택하며, 이는 **선별 휴리스틱**이지 품질 PASS가 아니다.
합성 변환 fixture만 PASS했다. 이 문장은 공개 데이터 추가 승인 전의
상태이고, 실제 다운로드·변환과 v3 교정은 아래 §12가 최신 판정을 소유한다.

훈련 승인 전 필수: 원천 라이선스와 20~50건 사람이 읽는 표본,
한국어/영어·단일/다회전 수량, tree별 train/val 분리, 중복·PII,
평가 benchmark/held-out 오염, mask 누출 0, context 초과 0 또는
명시 제외. 보호 `datasets/TinyDataset/**`에 접근하는 오염 검사는
별도 범위 승인 전 수행하지 않는다. 오염을 못 검사한 상태는
`NOT_RUN`이지 PASS가 아니다.

### 11.3 SFT pilot 선후관계와 사전 예측

| 순 | 단계 | 예측과 계속 조건 | 현재 |
|---|---|---|---|
| S0 | 공개 corpus 획득·출처/언어/중복/오염 감사 | 평가 누출 0, 한국어와 다회전 유효 표본 확보 | 변환기 합성 fixture만 PASS |
| S1 | 기존 32k tokenizer로 assistant-only mask·멀티턴 batch·CE 연결 | prompt target 정확히 0, assistant end 지도, 단일/다회전 positive-control overfit | CE 선결만 CPU PASS, full trainer `NOT_RUN` |
| S2 | 동일 부모 checkpoint의 SFT/no-SFT 대조, 한국어·영어 응답·형식·문맥과 full-val 망각 평가 | 형식/대화는 오를 수 있으나 새 사실·논리의 상승은 미확정. 망각 악화 시 중단 | GPU·모델 `NOT_RUN` |
| S3 | chat32 신규 pretrain 계보 후 S2와 공통 byte-bpb·행동 지표 대조 | 템플릿 비용은 줄 수 있으나 새 어휘의 품질·상주 대가는 미확정 | tokenizer 합성 fixture만 PASS |

기존 계획의 “6,000건 3 epoch”은 **조건부 목표**이지 현재 corpus 수량이나
실행 지시가 아니다. SFT 원본의 실제 assistant target token과 모델
context 길이를 세어 step×batch×seq와 과노출을 먼저 계산한다.
`check_run_registry.py`는 진행 중 큐의 런처·로그 잠금과 충돌하므로
이번 턴에는 실행하지 않았다. 새 실험 `.sh`도 작성하지 않는다.

### 11.4 이 단계가 답하지 못하는 것

마스크와 토크나이저 슬롯의 정적 계약은 실제 SFT 수렴·대화·지능 증거가
아니다. Aya는 대부분 단일턴이고 OASST 한국어 1,553은 **메시지 수**라
다회전 한국어 conversation 수를 보장하지 않는다. 공개 원천을
그대로 쓰면 benchmark 오염·품질·라이선스 하위 조건을 놓칠 수 있다.

## 12. 2026-09-23 원본 공개 SFT 확보와 독립 학습 진입점 — GPU 미실행

### 12.1 허용된 공개 원천과 별도 파생본

사용자가 라이선스가 명확한 공개 한·영 소스의 `HF/` 별도 확보를
승인했다. [Aya 공식 카드](https://huggingface.co/datasets/CohereLabs/aya_dataset)와
[OASST1 공식 카드](https://huggingface.co/datasets/OpenAssistant/oasst1)가
Apache-2.0이라고 표시하고, 함께 받은 README/LICENSE에서 이를
확인했다. pin은 §11.2와 같다. 네트워크 원본은 `HF/sft_sources`,
파생본은 `HF/sft_ready`에만 썼다. 명시한 저장 대상은 새 `HF/sft_sources`·`HF/sft_ready`였다. 기존 학습
캐시와 보호 `datasets/TinyDataset/**`의 내용은 열거나 수정하지 않았다.
다운로드의 일반 디스크 I/O가 진행 중 큐 계측에 준 영향은 미측정이다.

| 원천 | 다운로드 파일 SHA-256 | 의미 |
|---|---|---|
| Aya train parquet | `51baa85043b569ba117f41516b32d1b0e4e2647fb203a08933f98a556fb1fb06` | 사람 주석 single-turn 후보. 원문 품질·PII는 미감사 |
| OASST1 ready trees | `2a9a8fd343e9b28e04a895a669d3253f82d93e9c174d440199ae19d5fafbdff7` | tree당 best-rank 한 경로 선택. rank가 답 품질을 보증하지 않음 |

`p090_public_v1`을 보존하고, 현 `ko-en` tokenizer로 1024 입력
위치를 넘는 30건(전부 영어)을 제외한 `p090_public_v2`를 새 이름으로
만들었다. 이 선택과 각 출력 SHA는 v2 manifest에 기록된다.
사용한 1024는 이번 파생 필터이며 임의 parent checkpoint의 실제
`max_seq_len`과 같다는 주장은 아직 하지 않는다.

| split | 한국어 | 영어 | 합계 | 한국어 다회전 | 전체 다회전 | assistant target 비율 | 최대 직렬화 길이 |
|---|---:|---:|---:|---:|---:|---:|---:|
| train v2 | 176 | 2,827 | 3,003 | **0 (정정)** | 863 | 644,383/858,225 = 75.08% | 1,024 token |
| val v2 | **8** | 143 | 151 | **0** | 42 | 34,607/44,892 = 77.09% | 1,001 token |

mask empty=0, v2 manifest output SHA 일치, 1024초과=0은 CPU에서
확인했다. 이는 **변환·마스크 정적 계약**이지 한국어·영어 학습 품질이
아니다. 특히 한국어 val 8건, 한국어 다회전 val 0건으로 한국어
멀티턴 성능을 판정할 수 없다. 사용자 후속 결정 전 추가 소스를
무조건 섞지 않는다. [Aya Collection](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split)
한국어 train 두 shard는 합계 약 974 MB, Apache-2.0 표기지만
대규모 번역·템플릿 혼합으로 source별 조건과 평가 오염을 먼저
감사해야 한다. 현재 큐 중 추가 대형 다운로드는 보류한다.

### 12.2 기본 trainer를 건드리지 않는 SFT 경로

`scripts/train_sft_p090.py`를 별도 opt-in 진입점으로 신설했다.
기본 `tinylm/cli.py train`과 현재 큐 런처는 변경하지 않았다.

- 명시 `--execute`, 부모·토크나이저 SHA256, 같은 데이터 계보,
  manifest와 train/val 출력 SHA를 요구한다.
- 기존 tokenizer의 multi-token ChatML을 쓰고, chat32 신규 어휘는
  이전 checkpoint에 붙이지 못하도록 거부한다.
- 대화별 x/y를 분리하고 assistant-only target, 동적 batch padding
  `IGNORE=-100`, 유효 target 수로 gradient를 정규화한다. CE의 fp32
  임시 텐서는 기본 1,024 위치 청크로 제한하고 합성 값·gradient를 CPU 대조했다.
- 같은 구조의 parent state를 새 모델에 로드하고 opt-in AdamW 또는
  Muon RMS4를 선택할 수 있다. 기존 checkpoint·로그 파일 덮어쓰기를
  거부하고 별도 checkpoint·로컬 JSON을 만든다.
- contamination gate가 PASS가 아니면 `--pilot-only` 진단 모드만
  허용한다. 이때 결과 상태는 `PILOT_ONLY`; 공식 능력 승격 금지다.

합성 다회전/shift/pad/그룹 fixture는 CPU에서 PASS했다. **실제
checkpoint 로딩, forward/backward, CUDA, optimizer 안정성, 저장,
SFT val·full-val 망각·생성 능력은 모두 `NOT_RUN`**이다.
새 실험 `.sh`는 진행 중 큐 잠금에 따라 작성하지 않았다.
`check_run_registry.py`도 런처·로그를 읽을 수 있어 실행하지
못했으므로 태그·중복·VRAM preflight는 미완이다.

### 12.3 다음 게이트

1. 현재 큐 종료 후 P090의 parent checkpoint·tokenizer 계보,
   실제 context, 새 태그·출력 경로·VRAM·총 assistant token 예산을
   exact preflight로 고정한다. 이 전에는 GPU 명령을 권하지 않는다.
2. 공개 corpus 20~50건의 품질·PII·출처를 사람과 함께 점검하고,
   보호 held-out은 별도 정확 경로 승인 뒤에만 오염 검사한다.
3. 한국어 val과 다회전 부족을 해소하지 못하면 진단 pilot만 허용하고
   “한국어 멀티턴 개선”을 주장하지 않는다.
4. 모델 사용자 실행 뒤 동일 parent의 base/SFT, 한국어·영어,
   형식·단기문맥·논리 raw 답안, full-val 망각을 분리 판정한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 12.4 2026-09-23 v3 — 같은 질문의 교차 split 누출 제거

v2 감사에서 **train/val의 정규화 첫 질문이 1건 겹쳤다**.
OASST1의 다른 tree에 같은 첫 질문이 있었는데 tree ID만으로
split을 정했기 때문이다. 답변 원문은 로그·문서에 복사하지 않고
질문 SHA-256만 내부 감사에 사용했다. 기존 v1/v2는 덮어쓰지 않고
v3를 새 prefix로 생성했다.

`tinylm.data.sft.conversation_split_key`를 단일 소스로 두어
출처·tree가 달라도 NFKC·casefold·공백정규화한 첫 **사용자** 질문은
같은 split로 보낸다. system-first 대화의 공통 system 문구는 그룹 키가 아니다. 독립 SFT 학습 진입점도 train/val의 source ID와
첫 질문 중복을 **모델 로딩 전에** 거부한다. 합성 교차 출처 fixture
PASS, 실제 v3의 교차 첫 질문 중복 **0건**을 CPU에서 확인했다.

| split | 한국어 | 영어 | 합계 | 한국어 다회전 | 지도 target/전체 입력위치 | 빈 마스크 | 1024 초과 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3 train | 175 | 2,821 | 2,996 | **0** | 644,898/854,683 | 0 | 0 |
| v3 val | **9** | 149 | 158 | **0** | 34,092/45,280 | 0 | 0 |

v3 출력 SHA는 `HF/sft_ready/p090_public_v3_manifest.json`에
기록돼 일치했다. **앞서 v2 한국어 다회전 train 4건이라고
말한 것은 오류다.** v2의 OASST 한국어 레코드가 4건이었지만
그 네 건은 모두 단일턴이었다. v2·v3 모두 한국어 다회전은
train 0·val 0건이다. v3 val 한국어 9건은 일반 한국어 SFT
품질 판정에도 너무 적다. 이 오독은 새 모델 지능에 대한
어떤 긍정 판정에도 사용하지 않는다.
`contamination_gate=NOT_RUN`, PII·사람 품질검토·모델 학습
`NOT_RUN`을 유지한다. 원본 dataset 2종의 추가 다운로드나
실험 런처는 이 교정 때문에 자동으로 열리지 않는다.

## 13. 2026-09-23 한국어 SFT·실제 멀티턴 확대 — 사용자 승인, 큐 비간섭

사용자는 한국어 표본 부족 시 Aya Collection 등으로 확대하고, 실질 지능
로드맵 C안의 한국어 SFT·멀티턴 학습계획을 승인했다. 이 절은 **새 데이터의
적격성·분리 계약**이다. 모델 학습·큐 결과 판정은 여전히 `NOT_RUN`이며
[P100 원인분리](P100_40MiB-지식-형식-구조-원인분리.md)가 평가를 소유한다.

| 후보 | 카드상 규모·형식 | 현재 판정 |
|---|---|---|
| [Aya Collection 한국어](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split) | `kor` 4,161,353 prompt-completion 행, Apache-2.0 표기; 고정 revision `a3af2fde4b4cb5b2775830b11244a1a20b5f004f`, train parquet 2개 합계 973,675,125 bytes | **단일턴 확대 후보**. 템플릿·번역·인간주석 원천이 섞여 source별 권리·품질·중복 감사 전 학습 불가 |
| [한국어 공감형 다회전](https://huggingface.co/datasets/ohilikeit/empathetic_dialogues_mutli_turn_ko) | 26,662행, 22.2 MB, 카드상 Apache-2.0; GPT-3.5/4 합성, `single/multi_2/multi_3` 혼합 | **다회전 후보 조사 대상**. 실제 role 순서·원천 권리·중복·품질·답변 반복 패턴 확인 전 수량 인정/학습 불가 |
| [OpenLab 한국어 대화](https://huggingface.co/datasets/OpenLab-NLP/tiny-multiturn-chat-ko) | 425만 `context/prompt/answer` 행, Apache-2.0 표기 | 행이 독립 샘플일 수 있어 대화 ID·시간 순서·원본 라이선스 확인 전 다회전으로 환산 금지 |
| [Aka-LLAMA raw](https://huggingface.co/datasets/snupilab/aka-llama-korean-dataset-multiturn-raw) | 카드상 CC BY-NC 4.0과 하위 모델 라이선스 혼재 | **이번 permissive-first 훈련 원천에서 제외** |

### 13.1 자료 수집·변환 게이트

1. 이 절 작성 당시에는 큐 중 추가 다운로드를 보류했다. 후속 사용자 지시로
   **별도 HF 다운로드는 허용**됐고, 결과 로그·현재 큐 캐시 읽기는 금지,
   실험 런처는 읽기만 허용·수정 금지다(§14). Aya Collection은 원천별
   적격성 판단 뒤 pinned train 두 shard만 별도 HF 경로에 받으며
   test/val을 train에 섞지 않는다. 974 MB + 파생·임시공간을 계산한다.
2. 원천별 `dataset_name/sub_dataset_name/task_type/template_id`, 언어,
   split, 비어 있는 답, 길이, 중복률을 bounded-memory로 계측한다. 공식
   전체 데이터셋의 Apache 표기만으로 하위 원천의 모든 권리·안전성을
   통과시키지 않는다. source별 20~50건을 사람이 읽고 품질·PII·라이선스
   기록을 남긴 뒤 allowlist를 고정한다.
3. 기존 `conversation_split_key`로 출처가 달라도 첫 질문을 같은 split로
   묶고, 대화 원본에 tree ID가 있으면 tree 단위도 묶는다. train/val
   첫 질문·source ID 중복 0, 평가 benchmark 오염 0, mask empty 0,
   context 초과 0/명시 제외를 요구한다. 보호 held-out 검사는 별도
   정확 경로 승인 전 `NOT_RUN`으로 남긴다.
4. 다회전 원천은 인쇄된 `질문:/답변:` 문자열을 무비판적으로 토큰화하지
   않는다. role 분해, 턴 교대, 선행 history, 마지막 assistant target,
   원래 대화 ID를 확인한 뒤 canonical로 변환한다. 첫 질문 그룹을
   기준으로 train/val을 분리하고 한국어 실제 다회전 `train>0, val>0`을
   확인한다. 단순 role marker를 붙인 단일턴은 다회전으로 세지 않는다.
5. 실제 assistant target token 수, 1024 context 초과율, 어휘 범위,
   계보 SHA를 확인한 뒤 같은 parent의 format-only, 사실 QA,
   single-turn/multi-turn 팔을 **목표 지도 토큰 예산을 맞춰** 설계한다.
   출처·공감 스타일·턴 수가 함께 변하면 원인분리 불가로 판정한다.

이 절의 준비 상태는 `DESIGNED/STATIC_ONLY`이고 974 MB 취득,
사람 표본검토, 평가 오염, 한국어 다회전 적격 수량, GPU SFT와
생성 품질은 모두 `NOT_RUN`이다. 한국어 val 9건인 v3만으로
정식 한국어 SFT 승격을 허용하지 않는다.

## 14. 2026-09-23 별도 공개 SFT 원천 추가 확보 — train-ready 아님

사용자는 **현재 큐 진행 중에도 HF 다운로드를 허용**했다. 결과 로그 읽기는
계속 금지이고 실험 런처는 읽기만 허용·수정 금지다. 이 후속 선택은
§13 작성 당시의 다운로드 보류를 대체하지만 큐 결과 판정 권한은 아니다.
[원천별 확보 감사](../docs/20260923_한영일-SFT-멀티턴-공개원천-선별과-확보-감사.md)에
고정 revision·원본 SHA·언어/턴 집계·대체 번역 후보를 기록했다.

| 공개 원천 | 별도 `HF/sft_sources` 확보 | 현 gate |
|---|---|---|
| 한국어 공감형 멀티턴 후보 | 26,662행, 유형상 multi 18,568행 | GPT 합성·평문 턴 마커. 2,017행의 첫 질문 중복 경보. canonical 역할복원·사람 품질검토·오염 `NOT_RUN` |
| CarrotAI 한국어 단일턴 | 7,040행 | 정확한 쌍 중복 187, WizardLM 합성; `HOLD_QUALITY` |
| OASST2 사람 참여 대화 | ready tree 13,854개; 엄격 best-rank 동언어 경로 en 다회전 2,377, ja 다회전 24 | 영어 번역 pilot 1순위 후보, 일본어는 소규모 대조. OASST1 교차 중복·PII·품질 `NOT_RUN` |

확보한 원본·README 총 102,943,956 bytes를 새 폴더에만 저장했고
기존 cache·GPU·모델·학습·보호 자료 접근은 0건이다. 카드의 Apache-2.0
표기와 원본 SHA는 확인했지만, 하위 출처 권리·문장 품질·데이터셋 간
중복·eval 오염·assistant-only mask는 아직 통과하지 않았다.
한국어 공감형은 명시 `multi_2/multi_3` 표지를 그대로 다회전
학습 가능 건수로 승격하지 않는다. first-question/tree split, 실제
역할 순서와 assistant target 검증 뒤 재계수한다.

고품질 번역 대체는 OASST2 영어의 엄격한 다회전 후보에서 소량을
사람이 검토한 후 결정한다. 일본어는 [llm-jp-instructions](https://huggingface.co/datasets/llm-jp/llm-jp-instructions)
(사람 작성, 작은 단일턴)과 [JMultiWOZ](https://huggingface.co/datasets/nu-dialogue/jmultiwoz)
(사람 WoZ 멀티턴, task 지향)을 조사했으나 원본을 취득하거나
번역하지 않았다. Aya Collection 전량 974 MB도 원천별 적격성 미확인으로
미다운로드다. 새 실험 .sh·모델 평가·공식 품질 판정은 `NOT_RUN`이다.
