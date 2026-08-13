# P056 — **optimizer-step 양자화 캐시 + `aw` 재계산**

> **신설 2026-08-13**(사용자 승인). 출처: 외부 검토문서 A §2·§23 / 문서 B §11.
> 판정 전문 = [외부문서 분석 §R2](../docs/20260813_외부AI검토문서-5종-타당성분석.md).

---

## 1. ✅ 문서의 주장이 **사실이다** — 코드로 확인

```python
# tinylm/model/transformer.py  forward()
if not self._quant_frozen:      # ← 조건이 이것뿐. _quant_frozen 은 추론 전용
    self.refresh_quant()
```

→ **micro-batch 마다 전 모델 재양자화.** `steps 2289 × accum 16 = 36,624`회.
같은 optimizer step 안에서 **weight 는 안 바뀌므로 전부 같은 값**이다.

## 2. ⚠️ 그런데 이득은 문서 주장의 절반 이하다

| | 문서 | **우리 데이터 기준** |
|---|---|---|
| 속도 | "10%+" | ★**≤ 5%** |
| VRAM | 언급 | ★**−0.2 GiB 수준** |

**속도 상한 논증**(결과 034 §9): P042 가 **교사의 495M/스텝 재양자화를 통째로 없앴는데
속도 효과가 "측정 불가"** 였다(effect +1.95% vs drift 1.37%). 학생 몫은 그 **1.77배** →
넉넉히 5%.

**VRAM**: `_TernarySTE.forward` 가 `ctx.save_for_backward(aw, alpha)` 한다.
`aw = |W|` 는 **가중치 크기**(유니크 삼진 54.85M × 4B ≈ **219 MB**)이고 backward 까지 산다.
backward 에서 `abs(W)` 로 **재계산**하면 그만큼이 없어진다.

> ⚠️★**나는 초판 분석에서 "VRAM 이득 0 또는 음수" 라고 썼고 그건 틀렸다.**
> `_wq` 만 보고 `save_for_backward` 를 안 봤다. **순위는 안 바뀌지만 근거가 틀렸다.**

## 3. ★설계 — 문서 A §4 의 진단이 옳다

`_wq` 를 16회 backward 에 **그대로 재사용하면 안 된다** — autograd 그래프가 붙어 있어
graph 재사용 오류가 나고, `retain_graph=True` 로 우회하면 **VRAM 이 폭증**한다.

```
optimizer step 시작
  └ prepare_step_quant()   무거운 통계 1회 (q, alpha) — @torch.no_grad
micro 1..16
  └ _CachedTernarySTE.apply(w, q, alpha, ...)   그래프는 micro 마다 새로
opt.step() -> clear
```

**캐시하는 것**: `q`(삼진 forward 값), `alpha`(그룹 스케일, 가중치의 1/128)
**캐시 안 하는 것**: autograd 그래프, `aw`(backward 에서 `abs(W)` 재계산)

## 4. ★예측

| # | 예측 | 틀리면 |
|---|---|---|
| **P1** | 벽시계 **−2 ~ −5%** | 10% 넘으면 P042 상한 논증이 틀린 것 = 재검토 |
| **P2** | peak alloc **−0.15 ~ −0.25 GiB** | 훨씬 크면 계측을 의심 |
| **P3** | 🚫**비트 동일이 아니다** | autocast dtype 경계 때문 |
| **P4** | ★**gradient parity 가 `atol=0` 으로는 안 맞고 `1e-5` 급에서 맞는다** | 안 맞으면 구현 오류 |

## 5. 단계

**단계 0 — parity 게이트**(GPU 소, 수 분): 같은 seed/weight/입력에서
`max|Y_a − Y_b|`, `max|∇W_a − ∇W_b|`, **accum=16 optimizer step 후 `max|W'_a − W'_b|`**.
★**세 번째가 진짜 게이트**다 — forward 만 같으면 부족하다.

**단계 1 — 250스텝 × 2**(off/on) 같은 세션: `ms_step_median`·`peak_alloc`.

## 6. 판정

| 게이트 | 통과 |
|---|---|
| **G0** | optimizer step 후 weight 차 **< 1e-5** |
| **G1** | `ms_step_median` **−2% 이상** |
| **G2** | peak alloc **−0.1 GiB 이상** |
| 미달 | **채택 안 함** — 복잡도값을 못 한다 |

## 7. 한계

- ⚠️★**우선순위는 낮다.** −0.2 GiB 는 KD 손실 5.48 GiB 의 **4%** 다.
  같은 노력이면 **KD 제거(−7.41 GiB)가 37배** 크다.
- ⚠️ `_TernarySTE` 를 건드리므로 **모든 학습 경로에 위험**이 걸린다. 기본 off 필수.
- **3:4 희소·Arenas·커널 경로와 각각 parity 를 봐야 한다** — 조합이 넷이다.

## 8. preflight

- [x] 문서 주장을 **코드로 확인**하고 크기를 **우리 데이터로 상한**
- [x] 내 초판 오류(VRAM 0)를 **정정하고 기록**
- [x] **진짜 게이트가 forward 가 아니라 optimizer step 후 weight** 임을 명시
- [ ] `_CachedTernarySTE` 구현
- [ ] parity 테스트 · 배치

> **최근 갱신 2026-08-13** — 신설. **우선순위 낮음**(§7). 구현 전이라 배치 없음.
