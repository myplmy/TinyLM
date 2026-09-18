# TinyLM Muon RMS4의 Weight Decay 방법론 조사와 권고

> 작성: 2026-09-18  
> 상태: 연구·코드 근거 대조 완료, 기본 정책은 사용자 승인 반영  
> 증거 수준: 기존 학습 결과는 `MEASURED`, 이번 기본값 구현은 사용자 재스모크 전 `STATIC_ONLY`

## 1. 결론

TinyLM의 기본 학습 recipe는 **Muon RMS4, KD off**로 두되 weight decay(WD)는 모든
파라미터에 한 숫자를 일괄 적용하지 않는다. 현재 가장 근거가 강한 정책은 다음과 같다.

| 파라미터 종류 | optimizer | 권고 WD | 판정 |
|---|---|---:|---|
| TLinear의 일반 2-D 행렬(Q/K/V/O, MLP, projection) | Muon RMS4 | **0** | 결과 078의 직접 대조로 채택 |
| factorized embedding 및 Muon에서 제외된 일반 행렬 | AdamW | **0.1** | 기존 코드 정책 유지. 임베딩만의 독립 대조는 아직 없음 |
| norm, bias, residual gate, scale, shift, gain | AdamW | **0** | 크기·방향 파라미터에 불필요한 수축을 피하는 현 정책 유지 |
| Learnable Multiplier(LRM) | AdamW | **0.01** | 대칭성 표류 억제용 별도 정책. LRM 기능 자체는 기본 off |

따라서 CLI의 `--matrix-weight-decay` 기본값을 숫자 `0`으로 고정하는 대신 **`None`을
optimizer-aware routing의 표식으로 유지**한다. Muon 행렬에는 0, AdamW가 담당하는 embedding과
일반 행렬에는 모델의 0.1, norm·bias·gate 계열에는 0, LRM에는 0.01이 적용된다.

명시적 `--matrix-weight-decay X`는 실험용 override다. 이것을 지정하면 embedding이 아니라
Muon/AdamW의 일반 2-D 행렬 WD를 X로 맞추므로, 기본 recipe와 다른 실험임을 태그와 JSON에
남겨야 한다.

## 2. 용어와 방법론

### 2.1 L2 regularization과 decoupled weight decay는 같지 않다

SGD에서는 목적함수에 `λ‖W‖²/2`를 더하는 L2 벌점과 매 step 가중치를 수축하는 WD가 같은
형태로 정리되지만, Adam처럼 좌표별 preconditioner가 있는 optimizer에서는 같지 않다.
[AdamW](https://arxiv.org/abs/1711.05101)는 gradient에 L2 항을 섞지 않고 optimizer update와
분리해 `W ← (1−ηλ)W + optimizer_update`로 적용한다. TinyLM의 AdamW와 Muon WD도 이
**decoupled shrinkage** 계열이다.

실무적으로는 다음을 분리해야 한다.

1. **일반화 벌점**: 큰 가중치를 억제해 validation 성능을 개선하려는 목적.
2. **노름 제어**: scale-invariant 파라미터에서 유효 학습률이 너무 작아지는 것을 막는 목적.
3. **대칭성 표류 제어**: LRM처럼 서로 상쇄 가능한 승수의 무한 성장을 막는 목적.
4. **스케줄 결합**: 실제 수축량이 `η_t λ_t`이므로 LR/WSD 변화와 함께 해석하는 문제.

같은 숫자 `0.1`이라도 어느 목적과 parameter group에 쓰는지에 따라 의미가 다르다.

### 2.2 Muon에서 WD의 세기는 LR과 함께 읽어야 한다

TinyLM의 Muon은 기본 base LR `1e-3`에 RMS4 배율을 적용하므로 Muon 행렬 LR은 `4e-3`이다.
decoupled WD의 step당 수축은 대략 `ηλ`에 비례한다. 따라서 같은 `WD=0.1`을 AdamW 행렬과
Muon 행렬에 주면 Muon 쪽 명목 수축은 base-LR 기준으로 약 네 배 강하다. `0.1`이라는 숫자만
맞추는 것은 동일 정규화 강도를 뜻하지 않는다.

PyTorch의 [Muon 문서](https://docs.pytorch.org/docs/main/generated/torch.optim.Muon.html)도
Muon의 LR·WD를 별도 optimizer hyperparameter로 정의한다. 최근 대규모 Muon 연구는 update RMS
정렬과 WD가 장기 학습에서 중요하다고 보고하지만, 그 scale과 데이터 체급은 TinyLM과 다르다.
[Scalable Muon](https://arxiv.org/abs/2502.16982)의 방향은 참고하되 그 숫자를 복사하지 않는다.

### 2.3 Scale Weight Decay는 후속 연구 후보이지 현재 기본값이 아니다

[Scale Weight Decay and Train Better](https://arxiv.org/abs/2607.23777)는 LR 스케줄에 맞춰
WD를 scale하는 Muon-SW를 제안한다. WSD처럼 LR이 크게 변하는 TinyLM에는 개념적으로 맞지만,
현재 내부 직접 대조는 `constant matrix WD 0` 대 `0.1`뿐이다. 새 방법은 별도 계획에서
`η_t λ_t` 누적 수축을 맞춘 뒤 검증해야 하며, 논문 존재만으로 기본 정책에 넣지 않는다.

### 2.4 normalization이 있는 모델에서 WD는 유효 학습률도 바꾼다

[van Laarhoven](https://arxiv.org/abs/1706.05350)은 normalization이 있는 모델에서 WD가
함수 자체보다 weight norm과 그에 따른 유효 학습률을 조절할 수 있음을 보였다. TinyLM에는
RMSNorm과 QK-norm이 있으며 특히 Q/K projection은 출력이 scale-invariant한 구간이 있다.
그러므로 Q/K norm 증가를 감시할 가치는 있지만, 그 사실이 곧 모든 Muon 행렬에 WD를 켜야
한다는 뜻은 아니다. 먼저 optimizer-only update와 WD update를 분해 계측해야 한다.

## 3. TinyLM 내부 실측

정본은 [결과 078](../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md)이다.
같은 형상·풀·시드·스케줄에서 Muon 행렬 WD만 바꾼 직접 대조는 다음과 같다.

| Muon scale | matrix WD 0 | matrix WD 0.1 | `WD0 − WD0.1` | 판정 |
|---|---:|---:|---:|---|
| jordan×15 | **3.5407** | 3.5551 | **−0.0144** | WD0 우세 |
| RMS4 | **3.5279** | 3.5325 | **−0.0046** | WD0 우세 |

둘 다 paired full-val 자를 넘었고 부호가 같다. 따라서 현재 데이터·길이·스케줄에서
**Muon 행렬 WD0이 유일하게 직접 승리한 기본값**이다.

이 결과가 말하지 않는 것도 명확하다.

- `0`과 `0.1` 사이의 중간값은 시험하지 않았다. RMS4의 LR 배율을 감안한 `0.025`는 합리적인
  연구점이지만 `NOT_RUN`이다.
- embedding WD 0과 0.1은 독립 대조하지 않았다.
- WSD에 동기화한 WD, norm-targeted WD, Q/K만의 WD는 시험하지 않았다.
- 1.2B 계열 결과는 evaluation의 한국어 비율이 0%이므로 한국어 품질 근거가 아니다.

## 4. 현재 코드 라우팅의 타당성

`TMT.param_groups()`와 `split_params()`의 교집합을 기준으로 보면 다음 계약이 성립한다.

1. `nn.Embedding.weight`는 2-D지만 Muon에서 제외된다. lookup table에 Newton–Schulz
   직교화를 적용하지 않는다.
2. embedding을 포함한 AdamW 일반 행렬은 기존 `weight_decay=0.1` 그룹에 남는다.
3. 이름에 `scale`, `shift`, `gates`, `gain`, `bias`가 있거나 차원이 2보다 작은 파라미터는
   WD0 그룹이다.
4. LRM은 이름을 먼저 가로채 WD0.01 전용 그룹에 둔다. vector LRM도 nodecay로 새지 않는다.
5. Muon이 가져간 일반 2-D 행렬은 기본 WD0이며, 명시 override가 있을 때만 값이 바뀐다.

이 방식의 장점은 architecture와 optimizer에 맞지 않는 일괄 WD를 피하면서도 기존 embedding과
특수 파라미터 정책을 보존한다는 점이다. 단점은 `matrix_weight_decay=None`의 의미가 단순한
“WD 없음”이 아니라는 점이다. 그래서 로그와 JSON에 `matrix_weight_decay_effective`, AdamW
group별 WD, `muon_weight_decay`를 함께 남겨야 한다.

## 5. 적용/비적용 기준

### 5.1 현재 적용할 부분

- **Muon 일반 행렬: WD0.** 직접 실측 승자다.
- **AdamW embedding: WD0.1 유지.** 독립 증거는 없지만 기존 학습 계보를 보존한다.
- **LRM: 기능을 켠 경우 WD0.01.** 정규 regularization이라기보다 대칭성 표류 방지다.
- **WSD와 함께 로깅.** 최종 WD 숫자만이 아니라 LR 및 누적 `Ση_tλ_t`를 비교해야 한다.

### 5.2 적용하지 않을 부분

- norm, bias, residual gates, adaLN scale/shift, final norm scale에는 WD를 적용하지 않는다.
- KD off 결정을 WD로 되돌리지 않는다. KD 제거의 품질·속도·VRAM 이득은 별도 축이다.
- 모든 행렬에 AdamW식 `0.1`을 복사하지 않는다. Muon RMS4에서는 직접 열세였다.
- coupled L2를 “같은 WD”라고 부르지 않는다.

### 5.3 연구용으로만 남길 부분

| 후보 | 최소 대조 | 목적 | 현재 상태 |
|---|---|---|---|
| Muon normalized WD | `0` vs `0.025` | RMS4 LR 배율을 감안한 중간점 | `NOT_RUN` |
| embedding WD | `0` vs `0.1` | factorized embedding의 과소/과정규화 분리 | `NOT_RUN` |
| schedule-scaled WD | constant 0 vs matched cumulative shrinkage | WSD와 WD 결합 | `NOT_RUN` |
| Q/K norm-targeted WD | WD0 + norm audit vs 작은 WD | scale-invariance의 유효 LR 저하 검정 | `NOT_RUN` |
| LRM WD | `0.01` 주변 격자 | 표류 억제와 학습 자유도의 균형 | LRM 자체 기본 off |

이 실험들은 기준 프리셋 후보 비교와 한 배치에 섞지 않는다. optimizer, WD, architecture,
반복 노출을 동시에 바꾸면 어떤 축이 성능을 만들었는지 분리할 수 없다.

## 6. 검증 계약

기본값 변경 후 실제 학습에 들어가기 전 다음이 필요하다.

1. CPU 계약 검사에서 기본값이 Muon/RMS4/KD off이고 Muon 행렬 effective WD가 0인지 확인.
2. optimizer audit에서 각 parameter가 정확히 한 optimizer group에만 있고 누락이 없는지 확인.
3. total update를 `WD update + optimizer-only update`로 분리해 기록. WD0 팔에서는 WD update RMS가
   정확히 0이어야 한다.
4. 새 코드 상태에서 사용자가 smoke를 다시 실행. 종전 smoke PASS는 코드 변경 전 증거다.
5. GPU 본런은 같은 pool·tokenizer·seed·WSD·parent init 안에서만 비교하고 JSON final 및 paired
   evaluation을 정본으로 사용한다.

## 7. 최종 권고

현 시점의 제품·연구 기본은 **Muon RMS4 + matrix WD0 + KD off**다. 다만 이를 “모든 WD를
없앤다”로 요약하면 틀린다. 정확한 표현은 **optimizer-aware parameter-group WD**이며,
embedding 0.1, 특수 scale/bias 0, LRM 0.01을 각각 유지한다.

중간 WD나 schedule-scaled WD는 가치 있는 후속이지만, 먼저 6차 리뷰의 아키텍처·반복 노출
비교를 닫아야 한다. 현재 승격 결정에 미실험 WD를 추가하면 후보 네 안의 비교가 다시 교락된다.
