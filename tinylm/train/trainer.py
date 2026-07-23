"""학습 루프: 삼진 어닐 + LR 스케줄(cosine/wsd) + NaN 가드 + EMA + 베스트 체크포인트
+ train-val 모니터 + (선택) 조기 종료 / 부모초기화 / KD.

v6 효율/실험: WSD, EMA, best.pt, 조기종료, dense 부모초기화, dense 교사 KD, 층별 LoRA.
"""
from __future__ import annotations

import json
import math
import time

import torch
import torch.nn.functional as F

from .. import paths
from ..config import build_config
from ..model import TiedMLPTransformer
from ..data import prepare, Loader
from ..eval import evaluate
from .init_utils import init_from_dense, load_dense

CKPT = paths.RUNS / "ckpt"
LOGS = paths.RUNS / "logs"


def _lr_factor(s, warm, steps, sched, decay_frac=0.2):
    """warmup 후: cosine = 매끄러운 감쇠 / wsd = 긴 plateau + 마지막 decay_frac 감쇠."""
    if s < warm:
        return (s + 1) / warm
    p = (s - warm) / max(steps - warm, 1)
    if sched == "wsd":
        if p < 1.0 - decay_frac:
            return 1.0
        q = (p - (1.0 - decay_frac)) / decay_frac
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * q))
    return 0.1 + 0.45 * (1 + math.cos(math.pi * p))


def train(preset, arch, data, n_tokens, steps, micro_bs, seq, accum, lr, eval_every,
          resume=False, ckpt=True, compile_=False, *,
          sched="cosine", ema=0.0, early_stop=0, init_from=None,
          kd=False, kd_alpha=0.5, kd_temp=2.0, lora_rank=0, lora_bits=2, mlp_film=False,
          tag=None, tokstr=None, compile_mode="default"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(1337)
    if device == "cuda":                        # 저비용 성능 스위치
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True   # 고정 shape → cuDNN 오토튜너
        try:
            torch.set_float32_matmul_precision("high")   # fp32 matmul을 TF32로
        except Exception:
            pass
    CKPT.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)

    meta = prepare(data, n_tokens)
    cfg = build_config(preset, arch, seq, ckpt)
    cfg.mlp_lora_rank, cfg.mlp_lora_bits = lora_rank, lora_bits
    cfg.mlp_film = mlp_film
    model = TiedMLPTransformer(cfg).to(device)

    if init_from:
        init_from_dense(model, init_from, device)

    teacher = None
    if kd:
        teacher, _ = load_dense(kd if isinstance(kd, str) else CKPT / "dense.pt", device)
        teacher.eval(); teacher.set_anneal(1.0)
        for p in teacher.parameters():
            p.requires_grad_(False)
        print(f"[kd] 교사 로드 완료 (alpha={kd_alpha}, T={kd_temp})")

    if compile_:
        if compile_mode == "reduce-overhead":
            print("[compile] 주의: reduce-overhead(CUDA그래프)는 임베딩 타잉과 충돌해 "
                  "backward에서 크래시할 수 있습니다. 크래시 시 --compile-mode default 로 재실행하세요.")
        print(f'[compile] mode={compile_mode} — 첫 스텝은 수 분 걸릴 수 있습니다')
        model = torch.compile(model, mode=compile_mode)
    print(model.report())
    eff = micro_bs * accum * seq
    print(f"[{arch}] device={device}  {steps}step x {eff/1e3:.0f}K tok = "
          f"{steps*eff/1e6:.0f}M 토큰  (sched={sched} ema={ema} lora_r={lora_rank})\n")

    opt = torch.optim.AdamW(model.param_groups(lr), betas=(0.9, 0.95), eps=1e-8)
    base_lrs = [g["lr"] for g in opt.param_groups]
    warm = max(5, min(steps // 10, 100))

    tokstr = tokstr or (f"{int(n_tokens)//1_000_000}M" if n_tokens >= 10**6 else str(int(n_tokens)))
    _base = f"{preset}_{data}_{tokstr}"                # 스케일 프리픽스
    name = f"{_base}_{tag}" if tag else f"{_base}_{arch}"   # 태그도 스케일별 분리 → 클로버·오염 방지
    start = 0
    ck = CKPT / f"{name}.pt"
    ck_best = CKPT / f"{name}_best.pt"
    if resume and ck.exists():
        st = torch.load(ck, map_location=device)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); start = st["step"]
        print(f"[{arch}] step {start}에서 재개")

    params = [p for p in model.parameters() if p.requires_grad]
    shadow = [p.detach().clone() for p in params] if ema > 0 else None

    def _swap_in_ema():
        backup = [p.detach().clone() for p in params]
        for p, sh in zip(params, shadow):
            p.data.copy_(sh)
        return backup

    def _swap_out(backup):
        for p, b in zip(params, backup):
            p.data.copy_(b)

    # reduce-overhead(CUDA그래프)는 micro-step마다 그래프 출력 버퍼를 재사용하므로,
    # grad accum에서 각 forward 전에 step 경계를 표시해 backward가 덮인 버퍼를 참조하지 않게 한다.
    _cudagraph_step = (getattr(torch.compiler, "cudagraph_mark_step_begin", None)
                       if (compile_ and compile_mode == "reduce-overhead") else None)

    tr = Loader("train", micro_bs, seq, device, meta["dir"], seed=1234)
    va = Loader("val", micro_bs, seq, device, meta["dir"], seed=99)
    hist, t0, gmax, gpeak, n_skip = [], time.time(), 0.0, 0.0, 0
    best_val, best_step, since_improve = float("inf"), 0, 0

    def _do_eval(step, train_loss):
        nonlocal best_val, best_step, since_improve
        m = evaluate(model, va, 20, device); m["ema"] = False   # 주 지표 = raw 모델(실제 진행)
        line = (f"    >> val_loss {m['val_loss']:.4f}  ppl {m['ppl']:.2f}  "
                f"(train {train_loss:.3f}, val-train {m['val_loss']-train_loss:+.3f})")
        if shadow is not None:                                  # EMA는 부가 표시
            backup = _swap_in_ema()
            me = evaluate(model, va, 20, device)
            _swap_out(backup)
            m["val_ema"] = me["val_loss"]; line += f"  [ema {me['val_loss']:.4f}]"
        m.update(step=step, train_loss=train_loss, gap=m["val_loss"] - train_loss)
        hist.append(m); print(line)
        blob = {"model": model.state_dict(), "opt": opt.state_dict(),
                "step": step, "cfg": cfg.__dict__}
        if shadow is not None:
            blob["ema"] = [sh.detach().cpu() for sh in shadow]
        torch.save(blob, ck)
        if m["val_loss"] < best_val - 1e-4:                     # best 판정 = raw
            best_val, best_step, since_improve = m["val_loss"], step, 0
            torch.save(blob, ck_best)
            print(f"       best 갱신 {best_val:.4f} -> {ck_best.name}")
        else:
            since_improve += 1
        return m

    for s in range(start, steps):
        a0 = warm / steps + 0.05
        anneal = min(1.0, max(0.0, (s / steps - a0) / max(0.60 - a0, 1e-6)))
        model.set_anneal(anneal)
        f = _lr_factor(s, warm, steps, sched)
        for g, b in zip(opt.param_groups, base_lrs):
            g["lr"] = b * f

        model.train()
        tot = 0.0
        for _ in range(accum):
            x, y = tr()
            if _cudagraph_step is not None:
                _cudagraph_step()
            with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
                logits = model(x)
                ce = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1))
                if teacher is not None:
                    with torch.no_grad():
                        tlog = teacher(x)
                    T = kd_temp
                    kl = F.kl_div(F.log_softmax(logits.reshape(-1, cfg.vocab_size) / T, -1),
                                  F.softmax(tlog.reshape(-1, cfg.vocab_size) / T, -1),
                                  reduction="batchmean") * (T * T)
                    loss = ((1 - kd_alpha) * ce + kd_alpha * kl) / accum
                else:
                    loss = ce / accum
            loss.backward()
            tot += loss.item()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        if not torch.isfinite(gn):
            opt.zero_grad(set_to_none=True); model.clear_quant()
            n_skip += 1
            print(f"  [skip] step {s}: non-finite grad ({n_skip}회째)  "
                  f"anneal {model.cfg.quant_anneal:.2f}  lr {opt.param_groups[1]['lr']:.2e}")
            if n_skip > 20:
                print("  !! non-finite 20회 초과. LR을 낮추고 재시작하세요."); break
            continue

        gpeak = max(gpeak, float(gn))
        if s >= warm:
            gmax = max(gmax, float(gn))
        opt.step(); opt.zero_grad(set_to_none=True)
        if shadow is not None:
            with torch.no_grad():
                for sh, p in zip(shadow, params):
                    sh.mul_(ema).add_(p.detach(), alpha=1 - ema)
        model.clear_quant()

        if s % 10 == 0 or s == steps - 1:
            el = time.time() - t0
            print(f"  step {s:>5}/{steps}  loss {tot:.4f}  |g| {gn:.2f}  "
                  f"anneal {model.cfg.quant_anneal:.2f}  lr {opt.param_groups[1]['lr']:.2e}  "
                  f"{el/(s-start+1)*1000:.0f} ms/step")
        if (s + 1) % eval_every == 0 or s == steps - 1:
            _do_eval(s + 1, tot)
            if early_stop and since_improve >= early_stop:
                print(f"  [early-stop] {early_stop}회 연속 개선 없음 (best {best_val:.4f} @ {best_step}). 종료.")
                break

    final = evaluate(model, va, 100, device); final["ema"] = False
    if shadow is not None:
        backup = _swap_in_ema(); fe = evaluate(model, va, 100, device); _swap_out(backup)
        final["val_ema"], final["ppl_ema"] = fe["val_loss"], fe["ppl"]
    n_par = sum(p.numel() for p in model.parameters())
    res = {"arch": arch, "preset": preset, "data": data, "params": n_par, "steps": steps,
           "lr": lr, "seq": seq,
           "tokens": steps * eff, "final": final, "best_val": best_val, "best_step": best_step,
           "history": hist, "grad_max": gmax, "grad_peak_warmup": gpeak, "n_skip": n_skip,
           "sched": sched, "ema": ema, "kd": bool(kd), "init_from": bool(init_from),
           "lora_rank": lora_rank, "wall_sec": time.time() - t0}
    res["tag"] = name
    (LOGS / f"{name}.json").write_text(json.dumps(res, indent=2))
    print(f"\n[{arch}] 최종 val_loss {final['val_loss']:.4f}  ppl {final['ppl']:.2f}  "
          f"best {best_val:.4f}@{best_step}  ({n_par/1e6:.1f}M, {(time.time()-t0)/60:.1f}분, skip {n_skip})")
    return res
