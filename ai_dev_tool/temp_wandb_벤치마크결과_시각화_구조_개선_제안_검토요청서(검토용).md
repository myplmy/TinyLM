```markdown
# W&B 벤치마크 시각화 구조 개선 제안 검토서

## 1. 검토 목적

현재 W&B에는 각 모델의 벤치마크 결과가 기존 학습 Run의 Summary에 다음과 같은 형태로 저장되고 있다.

- `bench/hellaswag/acc`
- `bench/hellaswag/acc_norm`
- `bench/hellaswag/gold_ce`
- `bench/arc_easy/acc`
- `bench/piqa/acc_norm`
- ...

현재 방식은 개별 Run의 최종 수치를 확인하거나 Run Table에서 비교하는 데에는 문제가 없으나, 여러 모델 × 여러 벤치마크를 하나의 차트에서 비교하기에는 불편하다.

이에 기존 Summary 구조는 그대로 유지하면서 `wandb.Table`을 추가하고, W&B Workspace의 Custom Chart에서 범용적으로 시각화할 수 있도록 개선하는 방안을 검토 바람.

---

## 2. 기본 원칙

기존 프로젝트의 W&B 관련 설계 원칙은 유지한다.

1. 로컬 로그 및 결과 문서가 정본이며 W&B는 조회·시각화를 위한 사본이다.
2. 학습 경로에는 W&B hook을 추가하지 않는다.
3. W&B 업로드 실패가 학습이나 기존 로컬 결과에 영향을 주어서는 안 된다.
4. 현재처럼 벤치마크 결과는 가능한 한 해당 모델의 기존 학습 Run에 결합한다.
5. 벤치마크 전용 Run이나 dashboard용 관리 Run을 불필요하게 추가하지 않는다.
6. 50M token 미만 probe exclusion 등 기존 W&B 업로드 필터를 유지한다.
7. 현재 `bench/<task>/<metric>` Summary scalar를 제거하거나 다른 의미로 바꾸지 않는다.
8. W&B Table은 기존 결과의 새로운 정본이 아니라 시각화를 위한 파생 데이터로 취급한다.

---

## 3. 제안 구조

각 모델의 기존 W&B Run에 누적형 benchmark Table을 하나 추가하는 방안을 우선 검토한다.

예:

`bench/table`

Table은 wide format보다 long format을 사용한다.

예상 schema:

| model | task | metric | value | n | n_asked | skipped | seed | pmi |
|---|---|---|---:|---:|---:|---:|---:|---|
| mC_cla2_ag4_r20 | hellaswag | acc | 0.2814 | 5000 | 5000 | 0 | 99 | true |
| mC_cla2_ag4_r20 | hellaswag | acc_norm | 0.2606 | 5000 | 5000 | 0 | 99 | true |
| mC_cla2_ag4_r20 | hellaswag | gold_ce | 3.7108 | 5000 | 5000 | 0 | 99 | true |
| mC_cla2_ag4_r20 | arc_easy | acc | 0.3401 | 5000 | 2376 | 0 | 99 | true |
| mC_cla2_ag4_r20 | arc_easy | acc_norm | 0.3300 | 5000 | 2376 | 0 | 99 | true |
| mC_cla2_ag4_r20 | arc_easy | gold_ce | 6.7903 | 5000 | 2376 | 0 | 99 | true |
| mC_cla2_ag4_r20 | piqa | acc | 0.5337 | 5000 | 1838 | 0 | 99 | true |
| mC_cla2_ag4_r20 | piqa | acc_norm | 0.5745 | 5000 | 1838 | 0 | 99 | true |
| mC_cla2_ag4_r20 | piqa | gold_ce | 4.5992 | 5000 | 1838 | 0 | 99 | true |

핵심 컬럼은 다음 네 개다.

- `model`
- `task`
- `metric`
- `value`

나머지는 평가 조건 및 결과 해석을 위한 metadata다.

필요하다면 다음 항목의 추가도 검토 가능하다.

- `run_name`
- `preset`
- `train_tokens`
- `params`
- `metric_direction`
- `primary_metric`

단, 현재 코드에서 자연스럽게 얻을 수 있고 실제 분석에 필요한 경우에만 추가할 것.

---

## 4. 원하는 W&B Workspace 차트

이 Table의 핵심 목적은 Python에서 그래프를 생성해서 업로드하는 것이 아니라, W&B Workspace의 Custom Chart에서 직접 여러 모델을 비교하는 것이다.

최소한 다음 세 개 차트를 구성할 수 있어야 한다.

### 4.1 ACC

- X축: `task`
- Y축: `value`
- 색상/범례: `model`
- filter: `metric == "acc"`

예상 X축:

- hellaswag
- arc_easy
- piqa
- 이후 추가되는 benchmark

각 benchmark category 안에서 여러 모델의 값을 grouped bar 또는 이에 준하는 형태로 비교할 수 있어야 한다.

### 4.2 ACC_NORM

- X축: `task`
- Y축: `value`
- 색상/범례: `model`
- filter: `metric == "acc_norm"`

ACC와 동일한 형태이며 metric filter만 다르다.

### 4.3 GOLD_CE

- X축: `task`
- Y축: `value`
- 색상/범례: `model`
- filter: `metric == "gold_ce"`

`gold_ce`는 낮을수록 좋다는 점을 차트 제목 또는 설명에서 명확히 알 수 있도록 하는 방안을 검토한다.

---

## 5. 중요한 요구사항: 차트를 로컬에서 만들지 않을 것

현재 목적에 대해서는 matplotlib, Plotly 등으로 benchmark별 그래프를 Python에서 생성해서 W&B에 업로드하는 구조를 만들지 않는 방향을 우선한다.

이유는 다음과 같다.

- 새로운 모델이 추가될 때마다 그래프를 다시 생성해야 한다.
- 새로운 benchmark가 추가될 때마다 plot 코드를 수정하거나 다시 실행해야 한다.
- 모델 선택이나 metric 선택을 바꿀 때마다 정적 그래프를 재생성해야 한다.
- W&B Workspace / Custom Chart가 이미 이 역할을 수행할 수 있다.
- 로컬 plot은 논문·보고서용 정적 그래프나 특수한 통계 시각화가 필요한 경우에만 별도 도구로 만드는 편이 적절하다.

따라서 이번 개선의 목표는:

`데이터 업로드 구조 개선 → W&B Workspace가 그래프를 렌더링`

이어야 하며,

`Python에서 plot 생성 → 이미지/Plotly를 W&B에 업로드`

방식이 되어서는 안 된다.

---

## 6. 새 benchmark 추가 시 코드 변경 최소화

Table 구조는 특정 benchmark 이름을 코드에 하드코딩하지 않는 방향으로 설계한다.

향후 다음과 같은 benchmark가 추가되더라도:

- winogrande
- arc_challenge
- boolq
- mmlu
- mmlu_redux
- lambada
- gsm8k
- ifeval
- humaneval 계열
- 기타 신규 benchmark

가능하면 Table 생성 코드에는 별도 task-specific 분기를 추가하지 않아야 한다.

새로운 `task`와 새로운 numeric metric이 기존 `rec` 구조에 추가되면 자동으로 Table row로 들어가는 방식을 우선 검토한다.

단, `n`, `seed`, `pmi`, `skipped` 같은 metadata를 `metric/value` 행으로 변환해서는 안 된다.

예:

잘못된 구조:

| task | metric | value |
|---|---|---|
| hellaswag | seed | 99 |
| hellaswag | n | 5000 |

원하는 구조:

| task | metric | value | n | seed |
|---|---|---:|---:|---:|
| hellaswag | acc | 0.2814 | 5000 | 99 |
| hellaswag | acc_norm | 0.2606 | 5000 | 99 |

즉 실제 benchmark score와 평가 metadata를 구분할 것.

---

## 7. 증분 benchmark 실행 처리

이 부분은 중요하다.

벤치마크는 한 번에 전부 평가하지 않을 수 있다.

예:

```bash
python scripts/eval_bench_suite.py --task hellaswag ... --wandb
```

이후:

```bash
python scripts/eval_bench_suite.py --task piqa ... --wandb
```

그리고 나중에:

```bash
python scripts/eval_bench_suite.py --task arc_easy ... --wandb
```

처럼 실행할 수 있다.

이 경우 최종 `bench/table`은 반드시:

- hellaswag
- piqa
- arc_easy

결과를 모두 포함한 누적 snapshot이어야 한다.

PIQA 실행 시 기존 HellaSwag 행이 사라지거나, ARC-Easy 실행 시 PIQA만 남는 식의 덮어쓰기는 허용하지 않는다.

반대로 동일 benchmark를 다시 평가했을 때:

`(model, task, metric)`

이 동일한 row가 중복으로 계속 쌓이는 구조도 피한다.

재평가 시 어떤 값을 최신값으로 취급할 것인지 현재 프로젝트의 결과 저장 규약과 일치하도록 검토한다.

가능한 누적 원본 후보:

1. 로컬 정본으로부터 전체 benchmark 결과를 다시 수집
2. 기존 W&B Summary의 `bench/*` 값을 읽어 Table을 재구성
3. 기타 현재 프로젝트 구조에서 더 안전한 방법

정본 원칙 때문에 가능하면 로컬 결과로 재구성하는 방식이 더 적절한지 우선 검토할 것.

W&B에 이미 올라간 값을 다시 읽는 방식을 사용한다면 W&B가 정본이 되는 구조는 피해야 한다.

---

## 8. Summary와 Table의 역할 분리

기존 Summary는 그대로 유지한다.

예:

```text
bench/hellaswag/acc
bench/hellaswag/acc_norm
bench/hellaswag/gold_ce
bench/piqa/acc
bench/piqa/acc_norm
bench/piqa/gold_ce
```

역할:

### Summary

- 개별 Run에서 결과 빠르게 확인
- Runs Table에서 scalar 비교
- 기존 W&B 구조와의 호환성 유지
- 특정 metric 직접 조회

### Table

- 여러 benchmark를 하나의 공통 schema로 표현
- 여러 모델 간 비교
- W&B Custom Chart 데이터 소스
- task / metric 기반 filtering
- 향후 benchmark 확장

Summary와 Table이 서로 다른 계산 경로를 거쳐 값이 달라지는 구조는 피한다.

가능하면 동일한 `rec` 결과로부터 Summary와 Table row를 동시에 생성한다.

---

## 9. W&B Table 저장 방식 검토

현재 목적은 benchmark 결과의 최신 누적 snapshot을 사용하는 것이다.

따라서 W&B Custom Chart에서 Table을 읽을 때 `historyTable`보다 최신 snapshot을 읽는 `summaryTable` 방식이 적절한지 검토 바람.

벤치마크를 여러 차례 나누어 실행하면서 Table snapshot이 여러 번 기록될 수 있으므로, 과거 snapshot까지 모두 합쳐 동일 row가 여러 번 시각화되는 구조는 피해야 한다.

최종적으로 Workspace에서는 "현재 모델의 최신 benchmark 상태"만 나타나야 한다.

---

## 10. 모델 간 차트 구성 가능 여부 반드시 확인

구현 전에 W&B에서 다음 형태가 실제로 가능한지 확인할 것.

여러 모델의 서로 다른 Run 각각에 동일한 `bench/table` schema가 있을 때, Workspace의 하나의 Custom Chart가 선택된 여러 Run의 Table 데이터를 함께 읽어서 다음과 같이 표현 가능한가:

```text
X = task
Y = value
Color / Legend = model
Filter = metric == "acc"
```

예:

```text
                hellaswag        arc_easy          piqa

model_A             █               █               █
model_B             █               █               █
model_C             █               █               █
```

그리고 동일 chart 정의에서 filter만:

```text
metric == "acc_norm"
```

또는:

```text
metric == "gold_ce"
```

로 변경할 수 있어야 한다.

이 방식이 W&B의 실제 Table/Custom Chart 제약 때문에 불가능하거나 예상과 다르게 동작한다면 코드를 임의로 우회 구현하지 말고 먼저 그 제약을 보고할 것.

---

## 11. 차트 Y축 관련 제안

가능하다면 Workspace 구성 시:

### ACC / ACC_NORM

Y축 범위를:

```text
0 ~ 1
```

로 고정하는 방안을 권장한다.

모델 간 작은 차이를 자동 확대해서 과장하지 않기 위함이다.

### GOLD_CE

별도 Y축 범위를 사용하며, 차트 제목 등에:

```text
Gold CE ↓
```

또는 이에 준하는 표현을 사용해서 낮을수록 좋은 값임을 명확히 한다.

다만 이는 Python 코드에서 plot을 생성하라는 의미가 아니라 W&B Workspace의 chart 설정에 대한 제안이다.

---

## 12. 구현 최소화 원칙

이번 작업에서 불필요한 대규모 리팩터링은 하지 않는다.

특히 다음은 피한다.

- benchmark 전용 W&B 프로젝트 추가
- benchmark마다 별도 Run 생성
- benchmark마다 별도 Table key 생성
- benchmark마다 별도 Python plot 코드 작성
- matplotlib 이미지 업로드
- Plotly chart 자동 생성
- 기존 Summary 제거
- 기존 로컬 결과 형식 변경
- trainer.py 수정

현재의 W&B 사후 업로드 구조에 최소한의 변경으로 Table을 추가하는 방향을 우선한다.

---

## 13. 검증 항목

구현 후 최소한 다음을 검증할 것.

### 데이터

1. 기존 `bench/<task>/<metric>` Summary가 그대로 유지되는가.
2. 해당 모델 Run에 `bench/table`이 정상적으로 생성되는가.
3. Table의 `model`, `task`, `metric`, `value`가 올바르게 들어가는가.
4. `n`, `n_asked`, `skipped`, `seed`, `pmi`가 해당 score row와 함께 보존되는가.
5. 문자열이나 metadata가 score metric으로 잘못 들어가지 않는가.

### 증분 실행

6. HellaSwag 평가 후 PIQA만 추가 실행해도 두 benchmark가 모두 Table에 남는가.
7. 그 뒤 ARC-Easy만 실행해도 세 benchmark가 모두 남는가.
8. 기존 benchmark 재실행 시 동일 `(model, task, metric)` row가 중복 누적되지 않는가.

### 모델 비교

9. 서로 다른 모델 Run의 `bench/table` schema가 동일한가.
10. W&B Workspace Custom Chart에서 여러 모델을 동시에 비교할 수 있는가.
11. X=`task`, Y=`value`, Color=`model` 구성이 가능한가.
12. `metric == acc`, `acc_norm`, `gold_ce` filter로 세 차트를 구성할 수 있는가.

### 기존 규약

13. 50M token 미만 probe exclusion이 그대로 작동하는가.
14. W&B 오류가 기존 로컬 결과를 변경하지 않는가.
15. 기존 standalone W&B benchmark mode가 있다면 호환성이 깨지지 않는가.
16. 새 benchmark가 추가되어도 Table 생성 코드에 task별 별도 분기가 필요하지 않는가.

---

## 14. 보고 요청

우선 코드를 수정하기 전에 다음을 검토하여 보고 바람.

1. 현재 최신 코드에서 benchmark 결과가 W&B로 올라가는 정확한 경로
2. Table을 어느 함수/시점에서 생성하는 것이 가장 작은 변경인지
3. 누적 Table을 어떤 정본 데이터에서 재구성할 것인지
4. 여러 Run의 Table을 하나의 W&B Custom Chart에서 합쳐 `model`별 색상으로 표시할 수 있는지
5. `summaryTable` 기반 최신 snapshot 방식이 적절한지
6. 기존 Summary와 Table을 함께 유지할 때 발생할 수 있는 중복/불일치 위험
7. 예상 수정 파일 목록

검토 후 문제가 없다면 최소 변경으로 구현하고, 실제 W&B에서 위 세 종류의 차트를 구성할 수 있는 데이터 형태까지 확인할 것.

이번 작업의 최종 목표는 다음과 같다.

> **Python은 benchmark 결과와 범용 long-format Table까지만 W&B에 전달하고, 시각화는 W&B Workspace가 담당한다. 새로운 모델이나 benchmark가 추가되어도 plot 코드를 다시 작성하거나 그래프 파일을 재생성하지 않는다.**
```
