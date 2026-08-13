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


def _load(ckpt_name, dev):
    """체크포인트 → (model, cfg). ★`cfg` 는 저장된 것을 그대로 쓴다 — 재구성하지 않는다."""
    from tinylm.config import TMTConfig
    from tinylm.model.transformer import TiedMLPTransformer
    from tinylm import paths
    ck = Path(paths.RUNS) / "ckpt" / ckpt_name if not Path(ckpt_name).exists() else Path(ckpt_name)
    st = torch.load(ck, map_location=dev)
    cfg = TMTConfig(**st["cfg"])
    m = TiedMLPTransformer(cfg).to(dev)
    m.load_state_dict(st["model"], strict=False)
    m.eval()
    return m, cfg, ck


def _real_logits(a, dev):
    """★A2·A4 를 **실제 분포**에서 재기 위한 로짓. 학습 0, forward 만."""
    _hdr("--real : 실제 체크포인트 로짓")
    from tinylm.data import prepare, Loader
    tm, tcfg, tck = _load(a.teacher, dev)
    sm, scfg, sck = _load(a.student, dev)
    print(f"  교사 {tck.name}  ({tcfg.n_prelude}+{tcfg.n_middle}+{tcfg.n_coda}, "
          f"g{tcfg.mlp_group})")
    print(f"  학생 {sck.name}  ({scfg.n_prelude}+{scfg.n_middle}+{scfg.n_coda}, "
          f"g{scfg.mlp_group})")

    # ── ★A5 : 교사·학생의 양자화 규약이 같은가 ──────────────────────────────
    _hdr("A5  ★교사와 학생의 양자화 규약이 같은가 (2026-08-13 구현)")
    diffs = []
    for k in ("vocab_size", "quant_anneal", "micro_group", "twn_thr_ratio",
              "ste_clip", "quantize_embedding", "sparse34", "emb_rank"):
        tv, sv = getattr(tcfg, k, None), getattr(scfg, k, None)
        same = (tv == sv)
        print(f"    {k:20s} 교사 {str(tv):>8}   학생 {str(sv):>8}   "
              f"{'같다' if same else '★다르다'}")
        if not same:
            diffs.append((k, tv, sv))
    if not diffs:
        print("  ✅ A5 통과 — 규약이 같다. soft target 이 학생과 같은 좌표계에 있다")
    else:
        print(f"  ⚠️★A5 주의 — {len(diffs)}개가 다르다.")
        print("     ★`vocab_size` 가 다르면 KL 자체가 무효다(치명).")
        print("     `quant_anneal`·`micro_group` 이 다르면 교사 로짓이 **학생이 도달할 수 없는")
        print("     정밀도**에서 나온 것이라 soft target 이 체계적으로 어긋난다.")
        if any(d[0] == "vocab_size" for d in diffs):
            print("  🚫 **어휘가 다르다 — 아래 A2·A4 를 읽지 말 것**")

    meta = prepare(a.data, int(float(a.tokens.rstrip("Mm")) * 1e6), exact=True)
    va = Loader("val", a.bs, a.seq, dev, meta["dir"], seed=99)     # ★val 시드 99 고정
    x, y = va()
    with torch.no_grad():
        tl = tm(x).reshape(-1, tcfg.vocab_size).float()
        sl = sm(x).reshape(-1, scfg.vocab_size).float()
    N = sl.shape[0]
    print(f"\n  크롭 {a.bs}x{a.seq} = {N} 토큰 (val 시드 99)")
    tvd = 0.5 * (F.softmax(sl, -1) - F.softmax(tl, -1)).abs().sum(-1).mean().item()
    print(f"  ★실제 교사·학생 총변동거리 = {tvd:.4f}   "
          f"(합성 난수는 0.5206 이었다 — **비교하면 합성의 편향이 보인다**)")
    del tm, sm
    if dev == "cuda":
        torch.cuda.empty_cache()
    return sl.detach().clone(), tl, y.reshape(-1), N


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", type=int, default=32768)
    ap.add_argument("--rows", type=int, default=2048, help="B*T. 실전은 8192")
    ap.add_argument("--temp", type=float, default=2.0)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    # ★2026-08-13 구현 — 종전에는 docstring 에만 있고 없었다(결과 042 §4)
    ap.add_argument("--real", action="store_true",
                    help="★실제 체크포인트 로짓으로 A2·A4 를 다시 잰다(합성 편향 제거)")
    ap.add_argument("--teacher", default="m100_ko-en_300M_dense.pt")
    ap.add_argument("--student", default="m100R1c_ko-en_300M_mC_wsd.pt")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--seq", type=int, default=1024)
    a = ap.parse_args()
    V, N, T, al = a.vocab, a.rows, a.temp, a.alpha
    dev = a.device
    fails, notes = [], []
    print(f"torch {torch.__version__} / device {dev} / V={V} rows={N} T={T} alpha={al}")

    torch.manual_seed(1337)
    # ★★2026-08-13 정정 — **종전 합성 데이터가 퇴화였다.**
    #   교사·학생 로짓을 **같은 `base`** 에서 만들고 정답 로짓만 4.0 vs 3.2 로 달리 줬다.
    #   그러면 두 분포가 거의 같아 **KL ≈ 0**, gradient 도 ≈ 0 → A2 가 "실효비 0.000" 을
    #   찍었다. 그건 KD 구현의 성질이 아니라 **내 테스트 데이터의 성질**이다(결과 042 §3).
    #   → 교사와 학생을 **독립적으로 다르게** 만든다. 실제로 둘은 full-val 3.8080 vs 3.6984
    #     로 확연히 다른 분포다(결과 037 §1·040).
    tgt = torch.randint(0, V, (N,), device=dev)
    slog = torch.randn(N, V, device=dev) * 1.0
    tlog = torch.randn(N, V, device=dev) * 1.0                    # ★독립 난수 = 다른 분포
    slog[torch.arange(N), tgt] += 4.0                             # 학생이 정답을 더 확신
    tlog[torch.arange(N), tgt] += 3.2                             # 교사가 조금 못하다
    if a.real:
        slog, tlog, tgt, N = _real_logits(a, dev)
        V = tlog.shape[-1]
    slog.requires_grad_(True)
    with torch.no_grad():
        _js = 0.5 * (F.softmax(slog, -1) - F.softmax(tlog, -1)).abs().sum(-1).mean().item()
    print(f"  ★교사·학생 분포 차(총변동거리) = {_js:.4f}  "
          f"(0 에 가까우면 이 감사는 의미가 없다 — 결과 042 §3 의 실패)")
    if _js < 0.05:
        print("  🚫 두 분포가 너무 비슷하다. A2·A4 를 읽지 말 것.")
        notes.append("degenerate-data")

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
    # ★★2026-08-13 정정 (결과 042 §10) — **종전 A4 는 공허한 검사였다.**
    #   `torch.autocast` 의 **fp32 강제 목록**에 `log_softmax`·`softmax`·`kl_div` 가 들어 있다.
    #   즉 autocast 블록 안에서도 이 셋은 **fp32 로 실행된다.** 그래서 상대차가
    #   `0.000e+00` 로 **정확히 0** 이 나왔고, 이 검사는 **어떤 경우에도 실패할 수 없었다.**
    #   → ①autocast 가 실제로 fp32 를 쓰는지 **dtype 을 인쇄해 증명**하고
    #     ②**명시적 bf16** 경로를 대조군으로 둬서 검사에 실패 가능성을 만든다.
    with torch.no_grad():
        f32 = kd_kl(slog.detach().float(), tlog.float(), T).item()

        # (1) 증명: autocast 아래 log_softmax 의 실제 출력 dtype
        probe = slog.detach()[:2].float()
        if dev == "cuda":
            with torch.autocast("cuda", dtype=torch.bfloat16):
                ac_dtype = F.log_softmax(probe / T, -1).dtype
                bf_ac = kd_kl(slog.detach(), tlog, T).item()
        else:
            ac_dtype = torch.float32
            bf_ac = f32
        # (2) 대조군: **강제로** bf16 에서 log_softmax/softmax 를 돌린다
        bf_hard = kd_kl(slog.detach().bfloat16(), tlog.bfloat16(), T).float().item()

    rel_ac = abs(bf_ac - f32) / max(abs(f32), 1e-12)
    rel_hard = abs(bf_hard - f32) / max(abs(f32), 1e-12)
    print(f"  autocast 아래 log_softmax 출력 dtype = **{ac_dtype}**")
    print(f"    -^> torch 의 autocast 는 log_softmax·softmax·kl_div 를 **fp32 목록**에 둔다.")
    print(f"  fp32 KL      {f32:.6f}")
    print(f"  autocast KL  {bf_ac:.6f}   상대차 {rel_ac:.3e}")
    print(f"  ★강제 bf16 KL {bf_hard:.6f}   상대차 {rel_hard:.3e}   ^<- **이게 진짜 검사다**")
    if ac_dtype == torch.float32 and rel_ac == 0.0:
        print("  ✅ A4 통과 — **우리 학습 경로에는 위험이 없다.** autocast 가 fp32 로 지킨다")
        if rel_hard >= 1e-2:
            print(f"  ★참고: 강제 bf16 이면 KL 이 {rel_hard*100:.1f}% 바뀐다 — "
                  f"직접 `.bfloat16()` 캐스팅을 넣지 말 것")
    elif rel_ac < 1e-2:
        print("  ✅ A4 통과 — bf16 이 KL 을 1% 안에서 재현한다")
    else:
        print(f"  ⚠️★A4 주의 — autocast 경로가 KL 을 {rel_ac*100:.1f}% 바꾼다. "
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
        # ★2026-08-13 정정 — 종전에는 `history` 의 **순간값**만 봤고 표본이 안 모였다.
        #   원인은 "로깅이 없다" 가 아니라 ★**eval 격자와 KD 격자가 만나지 않는다** 였다:
        #     eval  s ≡ 99 (mod 100)   ·   KD  s ≡ 0 (mod kd_every=4)
        #     100 ≡ 0 (mod 4) 이므로 **99 mod 4 = 3 이 항상** — 주기 eval 은 **전부 비KD**,
        #     마지막 eval(s=steps−1) 하나만 KD 스텝에 걸린다. 23개 중 1개.
        #   → `trainer.py` 가 이제 **런 전체 누적 평균**을 json 최상위에 남긴다.
        mk = j.get("kd_step_loss_mean"); mn = j.get("nokd_step_loss_mean")
        ck = j.get("kd_step_ce_mean");   cn = j.get("nokd_step_ce_mean")
        if mk is not None and mn is not None:
            print(f"  {p.name[:40]:42s} KD {mk:.4f} / 비KD {mn:.4f}  차 {mk-mn:+.4f}"
                  f"   (n {j.get('kd_step_n')}/{j.get('nokd_step_n')})")
            if ck is not None and cn is not None:
                print(f"  {'':42s} ★순수 CE 로는 {ck:.4f} / {cn:.4f}  차 {ck-cn:+.4f}"
                      f"  ^<- **이쪽이 같아야 정상**")
            hit += 1
        else:
            hist = j.get("history") or []
            kdv = [h["train_loss"] for h in hist if isinstance(h, dict) and h.get("kd_step")]
            nov = [h["train_loss"] for h in hist if isinstance(h, dict) and h.get("kd_step") is False]
            print(f"  {p.name[:40]:42s} ⏸ 구 로그(누적 필드 없음). "
                  f"history 표본 KD {len(kdv)} / 비KD {len(nov)}")
    if not hit:
        print()
        print("  ⏸ **누적 필드를 가진 KD 런이 아직 없다.** 이건 결함이 아니라 순서다 —")
        print("     `trainer.py` 에 A3 계측을 2026-08-13 에 넣었으므로 **그 뒤의 KD 런부터** 나온다.")
        print("  ★위 목록의 `history 표본 KD 1 / 비KD 22` 가 격자 어긋남의 증거다:")
        print("     eval 은 s ≡ 99 (mod 100), KD 는 s ≡ 0 (mod 4) — **99 mod 4 = 3 이 항상**.")
        print("  ⚠️ **생략은 통과가 아니다.** 다음 KD 런이 이 항목을 자동으로 채운다.")

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
