#!/usr/bin/env python3
"""P034 단계1 — **실행시(상주) 메모리 실측**. 저장 MB 와 상주 MB 는 다른 값이다.

★왜: 우리가 보고해 온 "11.7MB / 2.64× 감축"은 `mem_breakdown()` 이 계산한
   **"삼진을 1.95(또는 1.25) bpw 로 패킹했다면"** 의 이론값이다. 그 패킹 포맷은 **아직 없다.**
   실행 중 실제로 들고 있는 것은 fp32 latent `weight` 와 fp32 dequant 사본 `_wq` 다.

★이 스크립트가 검정하는 예측 (P034 §1.1) — **틀리면 그게 더 좋은 소식이다**
   상주 메모리는 **bpw 와 무관**하고 **유니크 파라미터 수에만** 비례한다. 그렇다면:
     · 타잉(g↑) 은 유니크 수를 줄이므로 저장·상주 **둘 다** 줄인다      → 단조
     · 삼진·희소(bpw↓) 는 저장만 줄이고 상주는 **그대로**               → 기울기 0
   따라서 **mA(11.7MB 저장, g4)가 mC(14.9MB 저장, g8)보다 상주가 크다** —
   저장 순위와 상주 순위가 **뒤집힌다**. 이 역전이 관측되면 예측이 맞은 것이다.

두 가지 방법으로 동시에 잰다(둘 다 필요하다):
   RSS      — OS 가 보는 실제 점유. **단 PyTorch 는 해제분을 OS 에 즉시 안 돌려준다** → 과대 가능
   텐서합산 — 우리가 의도적으로 들고 있는 텐서의 바이트 합. 할당자 영향 없음 → 과소 가능
   진실은 두 값 사이에 있다. **한쪽만 보고 결론 내지 말 것.**

★2026-07-31 추가 — `--drop-latent` (P034 **단계2**)
   추론에는 backward 가 없으므로 fp32 latent `weight` 는 **죽은 무게**다. 이 플래그는
   `freeze_quant()` 직후 그것을 해제하고, **같은 표에서 해제 전/후를 나란히** 찍는다.
   함께 **로짓 동등성 게이트**를 돌린다 — 해제가 출력을 바꾸면 그건 최적화가 아니라 버그다.
   기대: 상주가 절반 근처로. 저장 MB 는 **변하지 않는다**(저장은 패킹 포맷의 이론값이다).

사용법
  python scripts/mem_runtime.py                       # 기본 3모델, CPU
  python scripts/mem_runtime.py --device cuda
  python scripts/mem_runtime.py --models mA_g4s34_k4
  python scripts/mem_runtime.py --drop-latent         # P034 단계2 (해제 전/후 대조)
"""
from __future__ import annotations
import argparse
import gc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MODELS = [("p6d", "dense"), ("mC_g8_k4", "tied"), ("mA_g4s34_k4", "tied")]
PROMPT = "대한민국의 수도 서울은"          # 한글이라 .bat 가 아니라 여기 산다


def rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 ** 2
    except ImportError:
        try:                                   # psutil 없으면 리눅스 폴백
            with open("/proc/self/statm") as f:
                return int(f.read().split()[1]) * 4096 / 1024 ** 2
        except Exception:
            return float("nan")


def tensor_mb(model):
    """의도적으로 들고 있는 텐서 바이트. latent / dequant 사본 / 그 외로 분해한다."""
    import torch
    lat = wq = other = 0
    tl = set()
    for m in model.modules():
        if hasattr(m, "_wq") and hasattr(m, "weight"):
            tl.add(id(m.weight))
            lat += m.weight.numel() * m.weight.element_size()
            if getattr(m, "_wq", None) is not None:
                wq += m._wq.numel() * m._wq.element_size()
            # ★P034 단계3: fp32 사본 대신 int8 코드 + fp32 α 를 든다. 둘 다 세야 한다.
            if getattr(m, "_i8", None) is not None:
                wq += m._i8.numel() * m._i8.element_size()
                wq += m._alpha.numel() * m._alpha.element_size()
            # ★★P014 단계1 — LUT 코드·per-row alpha 도 상주다. 안 세면 "삼진사본 0.0" 이 된다.
            if getattr(m, "_lut_codes", None) is not None:
                wq += m._lut_codes.numel() * m._lut_codes.element_size()
                wq += m._lut_alpha.numel() * m._lut_alpha.element_size()
            # ★★P034 단계3C(결과 016 §13): 언팩 캐시 버퍼. **이걸 안 세서 사고를 못 잡았다.**
            #   1차 구현이 dense 에서 fp32 20층분(472.5MB)을 들고 있었는데 이 함수는
            #   `parameters()` 와 `_wq`/`_i8` 만 보고 **86.9MB 라고 보고했다.**
            #   상주 회계는 "의도적으로 들고 있는 텐서" 전부여야 한다 — 파이썬 속성도 포함이다.
            c = getattr(m, "_i8_cache", None)
            if c is not None:
                wq += c.numel() * c.element_size()
    for p in model.parameters():
        if id(p) not in tl:
            other += p.numel() * p.element_size()
    # ★★★2026-08-23 실사고(결과 016 §단계5) — **임베딩 양자화 산출물이 회계에서 사라졌다.**
    #   `quantize_embedding` 은 `emb.weight` 를 **빈 텐서로 만들고** `_emb_code`/`_emb_scale`
    #   에 저장한다. 그런데 위 `model.parameters()` 루프는 **Parameter 만** 본다 →
    #   코드·스케일이 **한 바이트도 안 세어졌다.**
    #   결과: int8·int4·ternary 세 팔이 **전부 "기타 1.0 MB"** 로 같게 나왔고,
    #   **38.4 MB 라는 거짓 숫자**가 로그에 남았다.
    #   ⚠️★**결과 016 §13 이 이미 같은 사고를 겪었다**(언팩 캐시를 안 세서 86.9 라고 보고).
    #   **"상주 회계는 의도적으로 들고 있는 텐서 전부" 라는 규칙을 내가 다시 어겼다.**
    for _n in ("_emb_code", "_emb_scale"):
        _t = getattr(model, _n, None)
        if _t is not None:
            other += _t.numel() * _t.element_size()
    f = 1024 ** 2
    return lat / f, wq / f, other / f


def main():
    ap = argparse.ArgumentParser(description="P034 단계1 실행시 메모리 실측")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--kv-seq", type=int, default=1024,
                    help="★KV 캐시 상주을 잴 컨텍스트 길이(기본 1024 = 학습 seq). "
                         "KV 는 seq 에 선형이라 **한 수가 아니라 기울기**로 읽는다")
    ap.add_argument("--kv-bytes", type=int, default=4, choices=[1, 2, 4],
                    help="★KV 캐시 원소 바이트(기본 4 = fp32, 상주식과 같은 규약). "
                         "2 = bf16/fp16 캐시, 1 = int8 캐시(미구현 — 가정값)")
    ap.add_argument("--repeat-kv-reuse", action="store_true",
                    help="★재귀 통과 2회차 이후가 **첫 통과의 K/V 를 재사용**한다(P077 단계0). "
                         "엔트리가 `(owner, 통과)` 에서 `(owner, 0)` 으로 접혀 **KV 가 준다**. "
                         "기본 off = 비트 동일. ⚠️품질 대가는 `paired_eval` 이 잰다")
    ap.add_argument("--drop-latent", action="store_true",
                    help="P034 단계2 — freeze 후 fp32 latent 해제. 해제 전/후를 나란히 잰다")
    ap.add_argument("--int8-store", action="store_true",
                    help="P034 단계3 — 삼진 사본을 int8 코드+α 로. --drop-latent 와 함께 쓴다")
    ap.add_argument("--emb-quant", choices=["bf16", "fp16", "int8", "int4", "ternary"],
                    default=None,
                    help="(P034 단계5) 임베딩 양자화. ★bf16 은 복원이 없다(계산이 이미 bf16)")
    ap.add_argument("--emb-chunk", type=int, default=0,
                    help="(P034 단계5) 헤드를 어휘 축으로 자르는 크기. 0=끄기. 4096 이면 버퍼 4MiB")
    ap.add_argument("--lut", action="store_true",
                    help="★★(P014 단계1) LUT 배포 경로 — 삼진을 **1.600 bpw** 코드로. "
                         "int8(8비트)의 5배를 회수한다. ⚠️per-row alpha 로 재추정된다")
    ap.add_argument("--lut-out-chunk", type=int, default=0,
                    help="(P014) LUT gather 결과 (B,J,O) 를 출력채널로 나눈다. 0=한 번에")
    ap.add_argument("--unpack-cache", action="store_true",
                    help="P034 단계3C — int8 언팩을 유니크 모듈당 1회로. **로짓 게이트가 이걸 검증한다** "
                         "(캐시는 직전 텐서를 그대로 재사용하므로 0.000e+00 이 나와야 한다)")
    a = ap.parse_args()

    import torch
    from tinylm import paths
    from tinylm.infer.generate import load_model, sample
    from tinylm.data import tokenizer_path
    from tokenizers import Tokenizer

    models = ([(t, "dense" if t.startswith(("p6d", "dense", "p12d")) else "tied")
               for t in a.models] if a.models else DEFAULT_MODELS)
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    base = f"{a.preset}_{a.data}_{a.tokens}"

    print("=" * 96)
    print("  P034 단계1 — 실행시 메모리 실측 (저장 MB 는 이론·패킹 가정, 상주 MB 는 실측)")
    print(f"  device={a.device}  max_new={a.max_new}")
    print("  ★RSS 는 할당자 때문에 과대, 텐서합산은 임시버퍼를 빼서 과소. 둘을 함께 읽는다.")
    print("=" * 96)

    rows, skipped = [], []
    for tag, arch in models:
        ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {tag}")
            skipped.append(tag)
            continue
        gc.collect()
        if a.device == "cuda":
            torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        r0 = rss_mb()                                   # (a) 로드 전
        try:
            model, cfg, dev = load_model(arch=arch, ckpt_path=str(ck), device=a.device,
                                         emb_quant=a.emb_quant, emb_chunk=a.emb_chunk)
        except Exception as e:
            print(f"\n  [실패] {tag}: {type(e).__name__}: {e}")
            continue
        # load_model 이 freeze_quant() 까지 하므로 이 시점에 _wq 가 이미 존재한다.
        r1 = rss_mb()                                   # (b)(c) 로드 + 삼진화 후
        lat, wq, oth = tensor_mb(model)
        bd = model.mem_breakdown()
        packed = bd["total_mb"]
        nt = bd["params"]["ternary"]

        _ = sample(model, cfg, tok, PROMPT, max_new=a.max_new, temperature=0.7,
                   top_k=40, device=dev, stop_at_eos=False)
        r2 = rss_mb()                                   # (d) 생성 중/후 피크 근사
        peak_cuda = (torch.cuda.max_memory_allocated() / 1024 ** 2
                     if a.device == "cuda" else float("nan"))

        # ── P034 단계2 : latent 해제 (게이트 먼저, 그다음 재측정) ─────────────
        drop = None
        if a.drop_latent:
            ids = torch.tensor([tok.encode(PROMPT).ids], dtype=torch.long, device=dev)
            with torch.no_grad():
                before = model(ids).float().clone()
            model.drop_latent()
            if a.lut:
                # ★★P014 단계1 — LUT 배포 경로. **1.600 bpw.**
                #   ⚠️로짓 동등성 게이트가 **0 이 아니다** — per-row alpha 재추정 때문이다.
                #   그것이 이 경로의 알려진 대가이고, 아래 판정이 그 조건을 따로 인쇄한다.
                model.cfg.lut_out_chunk = int(a.lut_out_chunk or 0)
                model.to_lut()
            elif a.int8_store:
                model.to_int8()        # ★단계3 — 단계2 위에 얹는다(fp32 사본 → int8 코드+α)
                if a.unpack_cache:
                    model.enable_unpack_cache(True)   # ★단계3C — 게이트가 비트 동일성을 본다
            gc.collect()
            if a.device == "cuda":
                torch.cuda.empty_cache()
            with torch.no_grad():
                after = model(ids).float()
            dmax = float((before - after).abs().max())
            lat2, wq2, oth2 = tensor_mb(model)
            bd2 = model.mem_breakdown()
            r3 = rss_mb()
            drop = (lat2, wq2, oth2, lat2 + wq2 + oth2, bd2["packed_mb"], dmax, r3)
            del before, after, ids

        print(f"\n  ── {tag} ({arch}) " + "─" * 60)
        print(f"     저장(이론·패킹)   {packed:8.1f} MB     삼진 파라미터 {nt/1e6:6.2f}M "
              f"@ {bd['bpw_ternary']}bpw")
        print(f"     텐서합산 상주     {lat+wq+oth:8.1f} MB  "
              f"= latent {lat:.1f} + dequant사본 {wq:.1f} + 기타 {oth:.1f}")
        print(f"     RSS 로드전/로드후/생성후  {r0:8.1f} / {r1:8.1f} / {r2:8.1f} MB "
              f"(증가 {r2-r0:+.1f})")
        if a.device == "cuda":
            print(f"     CUDA 피크          {peak_cuda:8.1f} MB")
        print(f"     ★저장 대비 상주    {(lat+wq+oth)/packed:8.1f} 배")
        # ★★2026-08-29 신설 — KV 캐시 상주(REVIEW3 미지 8 / 핸드오프 Q1).
        #   가중치 상주와 **더하지 않고 따로** 인쇄한다. 합치면 기존 런 전부와 비교가 끊긴다(함정 2).
        try:
            # ★함정 39 — `eval()` 의 `visit_schedule()` 은 `train_repeat` 을 무시한다.
            #   재귀로 학습된 체크포인트는 **자기가 학습된 방문 수**로 재야 한다.
            _tr = float(getattr(cfg, "train_repeat", 1.0) or 1.0)
            _ir = float(getattr(cfg, "infer_repeat", 1.0) or 1.0)
            _rep = _tr if (_tr != 1.0 and _ir == 1.0) else None
            # ★P077 단계0 — `--repeat-kv-reuse` 는 **cfg 를 통해** kv_report 에 전달된다.
            #   🚫여기서만 켜면 `forward` 와 회계가 갈라진다(함정 40 계열) — cfg 를 바꾼다.
            if a.repeat_kv_reuse:
                cfg.repeat_kv_reuse = True
                model.cfg.repeat_kv_reuse = True
            _kv = model.kv_report(seq_len=a.kv_seq, kv_bytes=a.kv_bytes, repeat=_rep)
            _note = f" ★train_repeat {_tr:g} 로 셌다" if _rep else ""
            if a.repeat_kv_reuse:
                _note += " ★**KV 재사용 켬**"
            print(f"     ★KV 캐시          {_kv['kv_mb']:8.1f} MB  @ seq {a.kv_seq} "
                  f"({_kv['kv_kb_per_token']:.2f} KB/token · 엔트리 {_kv['kv_entries']}개 / "
                  f"방문 {_kv['kv_visits']}회 · {a.kv_bytes}B){_note}")
            print(f"                        ⚠️**seq 에 선형**이다 — 한 수가 아니라 기울기로 읽는다. "
                  f"cla_group↓·재귀↑ 가 엔트리를 늘린다")
        except Exception as _e:                                  # noqa: BLE001
            print(f"     ⚠️KV 회계 실패: {type(_e).__name__}: {_e}")
        if drop is not None:
            lat2, wq2, oth2, res2, pk2, dmax, r3 = drop
            if a.lut:
                # ★★2026-08-22 정정(함정 34) — 종전 기준 1.0 은 **내가 근거 없이 정한 값**이었고
                #   실측 1.615 를 "★실패" 로 찍었다. 🚫**max|dlogit| 는 품질 기준이 될 수 없다** —
                #   결과 028 이 잰 것은 **bpb** 이고 둘은 단위가 다르다. 로짓 절대차는
                #   softmax 를 지나면 크게 줄어들고, 그 감쇠율은 로짓 스케일에 의존한다.
                #   ★**여기서는 "죽지 않았는가" 만 본다**(NaN·발산). 품질 판정은
                #   `paired_eval` / `common_bpb` 가 소유한다.
                import math as _m
                gate = ("🚫NaN/Inf" if not _m.isfinite(dmax) else
                        "동작확인(품질 기준 아님)" if dmax < 20.0 else "⚠️비정상적으로 크다")
                _stg = "★P014 단계1 (latent 해제 + **LUT 1.600bpw**)"
            else:
                gate = "통과" if dmax == 0.0 else ("경계" if dmax < 1e-5 else "★실패")
                _stg = "단계2+3 (latent 해제 + int8 저장)" if a.int8_store else "단계2 (latent 해제)"
            print(f"     ── P034 {_stg} " + "─" * 30)
            if a.lut:
                print(f"     로짓 차이         max|dlogit| = {dmax:.3e}   {gate}")
                print(f"     ⚠️★**0 이 아닌 것이 정상**이다 — LUT 는 per-row alpha 로 재추정한다"
                      f"(768 에 5의 배수 약수가 없다).")
                print(f"     🚫★**이 숫자로 품질을 판정하지 않는다**(함정 34) — 결과 028 이 잰 것은"
                      f" **bpb**(+0.0038~0.0068)이고 로짓 절대차와 단위가 다르다.")
                print(f"     ★품질은 `paired_eval` 또는 `common_bpb` 로 따로 잰다.")
                print(f"     ★LUT 상주(코드+alpha) {model.lut_bytes()/2**20:8.2f} MiB  "
                      f"= 삼진 {model.mem_breakdown()['params']['ternary']/1e6:.2f}M x 1.600 bpw")
            else:
                print(f"     로짓 동등성 게이트  max|dlogit| = {dmax:.3e}   {gate}"
                      f"   (해제는 계산을 바꾸지 않으므로 0 이어야 한다)")
            print(f"     텐서합산 상주     {res2:8.1f} MB  "
                  f"= latent {lat2:.1f} + 삼진사본 {wq2:.1f} + 기타 {oth2:.1f}")
            print(f"     RSS 해제후        {r3:8.1f} MB")
            print(f"     ★상주 감축        {(lat+wq+oth)/max(res2,1e-9):8.2f} 배"
                  f"   (저장 {packed:.1f} -^> {pk2:.1f} MB — 저장은 변하지 않는 것이 정상)"
                  .replace("-^>", "→"))
        rows.append((tag, packed, lat, wq, oth, lat + wq + oth, r2 - r0, nt,
                     drop[3] if drop else None, drop[5] if drop else None))
        del model
        gc.collect()
        if a.device == "cuda":
            torch.cuda.empty_cache()

    # ★★2026-08-27 — **한 건도 못 쟀으면 조용히 0 으로 끝내지 않는다.**
    #   P074 단계1 의 [6/6] 이 네 태그 전부 "체크포인트 없음" 을 찍고 **종료코드 0** 을 냈다.
    #   배치는 성공으로 보였고, 로그를 눈으로 훑기 전까지 측정 0 건인 줄 몰랐다.
    #   결과 031 이 이미 같은 형태를 적어 뒀다 — *"runlog 가 명령을 조용히 버렸다"*.
    if not rows:
        print("\n" + "=" * 96)
        print(f"  🚫★**측정 0 건.** 요청한 {len(models)} 개 태그가 전부 없다: "
              f"{', '.join(skipped) if skipped else '(로드 실패)'}")
        print("  선행 학습 팔이 실패했거나 태그·프리셋이 틀렸다. **이 단계는 실패다.**")
        print("=" * 96)
        return 1
    if skipped:
        print(f"\n  ⚠️★건너뛴 태그 {len(skipped)} 개: {', '.join(skipped)} "
              f"— 아래 표는 **부분 측정**이다")
    if len(rows) < 2:
        return 0

    print("\n" + "=" * 96)
    print("  ★핵심 질문 1 — 저장 감축이 상주 감축으로 이어지는가")
    print("=" * 96)
    b = max(rows, key=lambda r: r[1])                   # 저장이 가장 큰 것 = dense 기준
    print(f"  기준 = {b[0]}  저장 {b[1]:.1f}MB  상주(텐서합산) {b[5]:.1f}MB\n")
    print(f"  {'모델':>16} {'저장MB':>8} {'저장감축':>9} {'상주MB':>9} {'상주감축':>9} {'전이율':>8}")
    print("  " + "-" * 68)
    for tag, packed, _l, _w, _o, res, _d, _n, _r2, _g in rows:
        s_red, r_red = b[1] / packed, b[5] / res
        print(f"  {tag:>16} {packed:8.1f} {s_red:8.2f}x {res:9.1f} {r_red:8.2f}x "
              f"{(r_red - 1) / (s_red - 1) if s_red > 1.001 else float('nan'):7.0%}")
    print("\n  전이율 = (상주감축-1)/(저장감축-1). 100% 면 저장 감축이 그대로 상주 감축이 된다.")

    print("\n" + "=" * 96)
    print("  ★핵심 질문 2 — 저장 순위와 상주 순위가 뒤집히는가 (단조성 검정)")
    print("=" * 96)
    by_store = sorted(rows, key=lambda r: r[1])         # 저장 작은 순
    by_res = sorted(rows, key=lambda r: r[5])           # 상주 작은 순
    print(f"  저장 작은 순: {' < '.join(r[0] for r in by_store)}")
    print(f"  상주 작은 순: {' < '.join(r[0] for r in by_res)}")
    if [r[0] for r in by_store] == [r[0] for r in by_res]:
        print("\n  → 순위 일치. **저장↓ 이 상주↓ 와 단조**다(비례까지는 위 전이율로 판단).")
    else:
        print("\n  → ★순위 역전. **저장 MB 로 모델을 고르면 상주 기준으로는 틀린 선택**이 된다.")
        print("     예측대로다: 상주는 bpw 가 아니라 유니크 파라미터 수를 따라간다.")
        print("     (타잉은 둘 다 줄이고, 삼진·희소는 저장만 줄인다)")
    print(f"\n  {'모델':>16} {'삼진파라미터':>12} {'저장MB':>8} {'상주MB':>9}")
    for tag, packed, _l, _w, _o, res, _d, nt, _r2, _g in sorted(rows, key=lambda r: r[7]):
        print(f"  {tag:>16} {nt/1e6:11.2f}M {packed:8.1f} {res:9.1f}")

    if a.drop_latent and any(r[8] for r in rows):
        print("\n" + "=" * 96)
        print("  ★핵심 질문 3 — latent 해제(P034 단계2)가 상주를 얼마나 줄이는가")
        print("=" * 96)
        print(f"  {'모델':>16} {'해제전':>9} {'해제후':>9} {'감축':>8} {'게이트':>12}")
        print("  " + "-" * 60)
        for tag, _p, _l, _w, _o, res, _d, _n, res2, dmax in rows:
            if res2 is None:
                continue
            print(f"  {tag:>16} {res:9.1f} {res2:9.1f} {res/res2:7.2f}x "
                  f"{('통과' if dmax == 0.0 else '★실패'):>12}")
        print("\n  · 이론 상한은 2.00배다(latent + dequant 두 벌 중 한 벌을 없앤다).")
        print("    2.00 에 못 미치는 부분이 임베딩·norm·gate 등 **삼진이 아닌** 파라미터다.")
        print("  · 게이트가 하나라도 실패하면 **감축 수치를 인용하지 말 것** — 다른 모델을 잰 것이다.")
        # ★순위가 바뀌는지 다시 본다. 로드맵 R2 가 묻는 것이 정확히 이 질문이다.
        o1 = [r[0] for r in sorted([r for r in rows if r[8]], key=lambda r: r[5])]
        o2 = [r[0] for r in sorted([r for r in rows if r[8]], key=lambda r: r[8])]
        print(f"\n  상주 순위 해제 전: {' < '.join(o1)}")
        print(f"  상주 순위 해제 후: {' < '.join(o2)}")
        print("  → " + ("순위 유지. 예측대로 둘 다 유니크 파라미터에 비례한다."
                        if o1 == o2 else
                        "★순위 변동. 예측이 빗나갔다 — 원인을 먼저 찾고 결론을 쓴다."))

    print("""
  ★한계
    · RSS 는 파이썬·torch 런타임을 포함하므로 '증가분'만 의미가 있다.
    · 텐서합산은 활성값·KV 캐시·임시버퍼를 제외한다 → 짧은 프롬프트 기준의 하한이다.
    · 이 측정은 **현재 구현**의 상주량이다. P034 단계2(latent 해제)·단계3(int8)·
      단계4(5비트 패킹)이 바로 이 수치를 줄이려는 작업이고, 여기가 그 기준선이다.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
