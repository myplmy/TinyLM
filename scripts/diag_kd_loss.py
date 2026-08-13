#!/usr/bin/env python3
"""P055 단계0 — **KD 구현 감사.** GPU 0~소 · 수 분. 학습 없음.

## 왜 이게 REVIEW2 보다 먼저인가

결과 038 이 **KD 가 300M 에서 해롭다**는 것을 두 시드에서 확정했다(+0.0208 / +0.0219,
그 조건 노이즈의 12~13배). 그런데 **왜** 해로운지는 모른다. 가설이 셋이고 **처방이 정반대**다:

| 가설 | 처방 |
|---|---|
| **H1** 교사가 학생보다 나쁘다 | 더 좋은 교사 |
| **H2** 구현에 결함이 있다 | ★**고치면 KD 가 되살아난다** |
| **H3** 이 예산에서 기법이 안 맞는다 | KD 를 버린다 |

> ★**모르는 채로 REVIEW2 가 KD 를 버리면, H2 였을 경우 버그 때문에 기법을 버린 것**이 된다.
> 이 스크립트는 **GPU 0** 으로 H2 를 배제(또는 확정)한다. 가장 값싼 순서다.

## 감사 항목 다섯 (계획 P055 §2.1)

| # | 무엇 | 왜 의심하나 |
|---|---|---|
| **A1** | `batchmean` 의 분모 | `(B·T, V)` 로 reshape 했으므로 분모가 **토큰 수**여야 한다 |
| **A2** | ★★`T²·α` 의 **실효 가중치** | `T=2` 면 `T²=4`. `α=0.5` 인데 **KL 항 gradient 가 CE 의 몇 배**인가 |
| **A3** | KD 스텝 / 비KD 스텝의 손실 스케일 불연속 | `kd_every=4` 라 4스텝 중 1스텝만 혼합손실이다 |
| **A4** | ★bf16 `log_softmax` | autocast 아래서 tail 확률이 뭉개지는가 |
| **A5** | 교사 어닐·그룹 규약이 학생과 같은가 | 교사는 자기 cfg 로 로드된다 |

⚠️ **사전 판단: 아마 버그는 없다.** 결과 006 이 **같은 코드로 100M 에서 −0.110 이득**을 쟀다.
그래도 감사하는 이유는 **비용이 거의 0** 이고 **틀렸을 때의 대가가 크기** 때문이다.
그리고 A2·A4 는 "버그" 가 아니라 **하이퍼파라미터 미탐색**일 수 있다 — 그쪽이 더 그럴듯하다.

사용:
    python scripts/diag_kd_loss.py                 # 합성 로짓(GPU 0 도 가능)
    python scripts/diag_kd_loss.py --real          # 실제 체크포인트 로짓
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                    # noqa: E402
import torch.nn.functional as F                                 # noqa: E402


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def kd_kl(slog, tlog, T):
    """`trainer.py` 의 식을 **그대로** 옮긴 것. 여기서 바꾸면 감사가 무의미하다."""
    return F.kl_div(F.log_softmax(slog / T, -1), F.softmax(tlog / T, -1),
                    reduction="batchmean") * (T * T)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", type=int, default=32768)
    ap.add_argument("--rows", type=int, default=2048, help="B*T. 실전은 8192")
    ap.add_argument("--temp", type=float, default=2.0)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    V, N, T, al = a.vocab, a.rows, a.temp, a.alpha
    dev = a.device
    fails, notes = [], []
    print(f"torch {torch.__version__} / device {dev} / V={V} rows={N} T={T} alpha={al}")

    torch.manual_seed(1337)
    # 학생·교사 로짓을 만든다. 교사가 **학생보다 조금 나쁜** 상황을 재현한다(결과 037 §1).
    tgt = torch.randint(0, V, (N,), device=dev)
    base = torch.randn(N, V, device=dev) * 0.5
    slog = base.clone(); slog[torch.arange(N), tgt] += 4.0        # 학생이 더 확신
    tlog = base.clone(); tlog[torch.arange(N), tgt] += 3.2        # 교사가 조금 못하다
    slog.requires_grad_(True)

    # ── A1 : batchmean 의 분모 ───────────────────────────────────────────────
    _hdr("A1  batchmean 의 분모가 토큰 수인가")
    kl = kd_kl(slog, tlog, T)
    # 손 계산: sum(KL) / N * T^2
    with torch.no_grad():
        manual = (F.kl_div(F.log_softmax(slog / T, -1), F.softmax(tlog / T, -1),
                           reduction="sum") / N * (T * T)).item()
    d = abs(kl.item() - manual)
    print(f"  코드 값 {kl.item():.6f}   손 계산(sum/N*T^2) {manual:.6f}   차 {d:.2e}")
    if d < 1e-4:
        print("  ✅ A1 통과 — 분모가 **행 수(=토큰 수)** 다. 표준 KD 규약과 일치")
    else:
        print("  🚫 A1 실패 — 분모가 예상과 다르다")
        fails.append("A1")

    # ── A2 : T^2 * alpha 의 실효 가중치 ──────────────────────────────────────
    _hdr("A2  ★KL 항과 CE 항의 gradient 크기 비 — alpha 가 의도한 대로인가")
    slog.grad = None
    ce = F.cross_entropy(slog, tgt)
    ce.backward(retain_graph=True)
    g_ce = slog.grad.norm().item()
    slog.grad = None
    kd_kl(slog, tlog, T).backward()
    g_kl = slog.grad.norm().item()
    ratio = g_kl / max(g_ce, 1e-12)
    eff = al * ratio / max((1 - al) * 1.0, 1e-12)
    print(f"  ||d(CE)/d(logit)||  = {g_ce:.6f}")
    print(f"  ||d(KL)/d(logit)||  = {g_kl:.6f}   (T^2 포함)")
    print(f"  ★크기 비 KL/CE      = {ratio:.3f}")
    print(f"  ★손실 `(1-a)*CE + a*KL` 의 **실효 gradient 비** = {eff:.3f} : 1")
    print(f"    (a={al} 이면 명목상 1:1 이어야 한다)")
    if 0.5 <= eff <= 2.0:
        print("  ✅ A2 통과 — 명목 alpha 와 실효 가중치가 같은 자릿수")
    else:
        print(f"  ⚠️★A2 주의 — **실효 비가 {eff:.2f}:1 이다.** "
              f"alpha={al} 이라고 썼지만 실제로는 alpha_eff = {eff/(1+eff):.3f} 로 동작한다.")
        print("     -^> 이건 '버그' 가 아니라 **미탐색 하이퍼파라미터**다. "
              "P055 단계1(alpha 스윕)이 바로 이걸 잰다.")
        notes.append("A2")

    # ── A4 : bf16 log_softmax ───────────────────────────────────────────────
    _hdr("A4  ★autocast(bf16) 아래 log_softmax 가 tail 을 뭉개는가")
    with torch.no_grad():
        f32 = kd_kl(slog.detach().float(), tlog.float(), T).item()
        if dev == "cuda":
            with torch.autocast("cuda", dtype=torch.bfloat16):
                bf = kd_kl(slog.detach(), tlog, T).item()
        else:
            bf = kd_kl(slog.detach().bfloat16().float(), tlog.bfloat16().float(), T).item()
    rel = abs(bf - f32) / max(abs(f32), 1e-12)
    print(f"  fp32 KL {f32:.6f}   bf16 경로 KL {bf:.6f}   상대차 {rel:.3e}")
    if rel < 1e-2:
        print("  ✅ A4 통과 — bf16 이 KL 을 1% 안에서 재현한다")
    else:
        print(f"  ⚠️★A4 주의 — bf16 경로가 KL 을 {rel*100:.1f}% 바꾼다. "
              f"soft target 의 tail 이 KD 의 핵심이므로 무시할 수 없다.")
        notes.append("A4")

    # ── A3 · A5 : 로그·체크포인트 기반(있으면) ────────────────────────────────
    _hdr("A3  KD 스텝 / 비KD 스텝의 손실 스케일 불연속 (기존 json 에서 읽는다)")
    logs = sorted((Path(__file__).resolve().parent.parent / "runs" / "logs").glob("*.json"))
    hit = 0
    for p in logs:
        try:
            import json
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not j.get("kd"):
            continue
        hist = j.get("history") or j.get("metrics") or []
        kdv = [h["train_loss"] for h in hist if isinstance(h, dict) and h.get("kd_step")]
        nov = [h["train_loss"] for h in hist if isinstance(h, dict) and h.get("kd_step") is False]
        if len(kdv) >= 3 and len(nov) >= 3:
            mk, mn = sum(kdv) / len(kdv), sum(nov) / len(nov)
            print(f"  {p.name[:46]:48s} KD스텝 {mk:.4f} / 비KD {mn:.4f}  차 {mk-mn:+.4f}")
            hit += 1
    if not hit:
        print("  (KD 런의 스텝별 기록을 못 찾았다 — json 에 history 가 없으면 이 항목은 생략된다)")
        print("  ⚠️ **생략은 통과가 아니다.** 다음 KD 런의 콘솔에서 `[KD혼합]` 표시가 붙은 줄과")
        print("     안 붙은 줄의 손실 크기를 눈으로 비교할 것.")

    # ── 판정 ────────────────────────────────────────────────────────────────
    _hdr("판정 — H2(구현 결함)가 있는가")
    if fails:
        print(f"  🚫 실패: {', '.join(fails)}  -^> ★**H2 확정. 고치기 전에는 KD 판정을 하지 않는다.**")
    elif notes:
        print(f"  ⚠️ 주의: {', '.join(notes)}  -^> **버그는 아니지만 미탐색 축이 있다.**")
        print("     ★P055 단계1(kd_alpha 스윕 0.5/0.3/0.1/0)이 이것을 직접 잰다.")
    else:
        print("  ✅ 감사 통과 — **H2 는 배제된다.** 남은 것은 H1(교사)·H3(예산 의존)이고")
        print("     둘 다 `kd_alpha` 스윕(단계1)이 갈라 준다.")
    print()
    print("  ⚠️ **이 감사는 합성 로짓으로 했다.** 실제 분포에서 A2·A4 의 크기는 다를 수 있다.")
    print("     단 A1 은 수식 항등이라 분포와 무관하다.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
