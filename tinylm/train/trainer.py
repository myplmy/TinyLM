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
    """cosine / wsd(긴 plateau+감쇠) / stable(warmup+평탄, plateau 생성용) /
    decay(워밍업 없이 peak→0.1 cooldown, plateau에서 분기)."""
    if sched == "decay":                          # cooldown-only (decay-branch)
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * s / max(steps, 1)))
    if s < warm:
        return (s + 1) / warm
    p = (s - warm) / max(steps - warm, 1)
    if sched == "stable":                         # plateau: 감쇠 없이 평탄
        return 1.0
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
          tag=None, tokstr=None, compile_mode="default", mlp_group=None, ema_start=0.0,
          center_weights=False, decay_from=None, snapshots=None,
          use_ternary_kernel=False, ternary_kernel_triton=False,
          kd_cache=False, kd_topk=16, kd_every=1, kd_dynamic=False, sparse34=False,
          pool_tokens=None, exact_cache=False):
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

    # 데이터 풀(캐시)은 pool_tokens 로 학습길이·이름과 분리 가능. 미지정이면 기존처럼 n_tokens.
    #   토큰스윕(P007 클린): 모든 예산을 동일 600M 풀에서 샘플 → pool_tokens=600M, exact_cache=True.
    meta = prepare(data, int(pool_tokens) if pool_tokens else n_tokens, exact=exact_cache)
    cfg = build_config(preset, arch, seq, ckpt)
    if mlp_group and arch == "tied":            # g 스윕용 오버라이드(P003)
        assert cfg.n_middle % mlp_group == 0, f"n_middle {cfg.n_middle} % g {mlp_group} != 0"
        cfg.mlp_group = mlp_group
    cfg.mlp_lora_rank, cfg.mlp_lora_bits = lora_rank, lora_bits
    cfg.mlp_film = mlp_film
    cfg.center_weights = center_weights
    cfg.use_ternary_kernel = use_ternary_kernel
    cfg.ternary_kernel_triton = ternary_kernel_triton
    cfg.sparse34 = sparse34
    if sparse34:
        assert cfg.micro_group % 4 == 0, "sparse34 는 micro_group 이 4의 배수여야 함"
        if use_ternary_kernel:
            raise SystemExit("[sparse34] 커스텀 삼진 커널 경로는 3:4 미구현 — "
                             "--sparse34 는 표준(F.linear) 경로에서만 사용하세요(커널 병용 금지).")
        print("[sparse34] 3:4 희소 삼진(1.25bpw) 활성 — 각 4-블록 |w|최소 1개 0강제")
    model = TiedMLPTransformer(cfg).to(device)

    if init_from:
        init_from_dense(model, init_from, device)

    teacher = None
    if kd and not kd_cache:
        teacher, _ = load_dense(kd if isinstance(kd, str) else CKPT / "dense.pt", device)
        teacher.eval(); teacher.set_anneal(1.0)
        for p in teacher.parameters():
            p.requires_grad_(False)
        if compile_:
            teacher = torch.compile(teacher)   # KD 가속: 교사 forward도 컴파일(eager→컴파일)
        print(f"[kd] 교사 로드 완료 (alpha={kd_alpha}, T={kd_temp})")

    if decay_from:                              # WSD decay-branch: plateau에서 분기
        from .init_utils import _strip
        st = torch.load(decay_from, map_location=device)
        model.load_state_dict(_strip(st["model"]))
        print(f"[decay] plateau 로드 -> cooldown {steps}스텝  <- {decay_from}")

    if compile_ and (use_ternary_kernel or ternary_kernel_triton):
        # 커널 경로는 torch.compile 과 근본적으로 상성이 나쁘다:
        #   - Triton 커스텀 커널은 dynamo 의 identify_mutated_tensors 가 커널 IR 을 파싱하다
        #     CompilationError(IndexError: Function argument index out of range) 로 크래시.
        #   - anneal>=1.0 데이터 의존 분기 → 그래프 브레이크 + quant_anneal 값 가드 재컴파일 폭주.
        # 따라서 두 옵션 동시 사용은 조용히 느려지거나 크래시하므로 **여기서 학습을 중단**한다.
        raise SystemExit(
            "[중단] --ternary-kernel[-triton] 은 --compile 과 함께 쓸 수 없습니다.\n"
            "  이유: dynamo 가 커스텀 Triton 커널 IR 파싱 중 크래시(IndexError)하거나, anneal 데이터의존\n"
            "        분기로 재컴파일 폭주가 발생합니다(커널은 별도 최적화 경로라 compile 대상이 아님).\n"
            "  조치: 커널 벤치는 --compile 을 빼고 실행하세요. 예)\n"
            "        python run100m.py train ... --ternary-kernel --ternary-kernel-triton   (--compile 제거)")
    if compile_:
        if compile_mode == "reduce-overhead":
            print("[compile] 주의: reduce-overhead(CUDA그래프)는 임베딩 타잉과 충돌해 "
                  "backward에서 크래시할 수 있습니다. 크래시 시 --compile-mode default 로 재실행하세요.")
        print(f'[compile] mode={compile_mode} — 첫 스텝은 수 분 걸릴 수 있습니다')
        model = torch.compile(model, mode=compile_mode)
    tokstr = tokstr or (f"{int(n_tokens)//1_000_000}M" if n_tokens >= 10**6 else str(int(n_tokens)))
    _base = f"{preset}_{data}_{tokstr}"
    name = f"{_base}_{tag}" if tag else f"{_base}_{arch}"   # 스케일별 이름(클로버·오염 방지)
    label = tag or arch                                    # 로그 표시용(예: t_kd_g8 / tied)
    print(model.report())
    eff = micro_bs * accum * seq
    print(f"[{label}] device={device}  {steps}step x {eff/1e3:.0f}K tok = "
          f"{steps*eff/1e6:.0f}M 토큰  (sched={sched} ema={ema} lora_r={lora_rank})\n")

    opt = torch.optim.AdamW(model.param_groups(lr), betas=(0.9, 0.95), eps=1e-8,
                            fused=(device == "cuda"))   # ①: optimizer update 단일 커널
    base_lrs = [g["lr"] for g in opt.param_groups]
    warm = 0 if sched == "decay" else max(5, min(steps // 10, 100))
    # 토큰 마크별 명명 스냅샷: {마크토큰: 라벨}. decay-branch 소스로 재사용.
    snap_steps = {}
    for tok in (snapshots or []):
        stp = max(1, round(int(tok) / eff))
        lbl = f"{int(tok)//1_000_000}M" if int(tok) >= 10**6 else str(int(tok))
        snap_steps[stp] = lbl

    start = 0
    ck = CKPT / f"{name}.pt"
    ck_best = CKPT / f"{name}_best.pt"
    if resume and ck.exists():
        st = torch.load(ck, map_location=device)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); start = st["step"]
        print(f"[{arch}] step {start}에서 재개")

    kd_reader = None
    if kd_cache:
        from .kd_cache import KdCacheReader
        kd_reader = KdCacheReader(_base, kd_topk, micro_bs, seq)
        kd_reader.seek_step(start, accum)
        print(f"[kd-cache] 오프라인 KD 캐시 사용 (top{kd_topk}, 교사 forward 없음)")

    params = [p for p in model.parameters() if p.requires_grad]
    shadow = None                               # P1: 후반부(ema_start 이후)에만 지연 생성·누적
    ema_start_step = int(ema_start * steps)

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

    bpt = meta.get("bytes_per_token")           # bits-per-byte용(토크나이저 무관 지표)
    tr = Loader("train", micro_bs, seq, device, meta["dir"], seed=1234)
    va = Loader("val", micro_bs, seq, device, meta["dir"], seed=99)
    hist, t0, gmax, gpeak, n_skip = [], time.time(), 0.0, 0.0, 0
    best_val, best_step, since_improve = float("inf"), 0, 0
    n_kd_fwd = 0                                 # 실제 교사 forward를 수행한 스텝 수(가속 측정용)

    def _do_eval(step, train_loss):
        nonlocal best_val, best_step, since_improve
        m = evaluate(model, va, 50, device, bytes_per_token=bpt); m["ema"] = False   # 주 지표 = raw
        line = (f"    >> val_loss {m['val_loss']:.4f}  ppl {m['ppl']:.2f}  "
                f"(train {train_loss:.3f}, val-train {m['val_loss']-train_loss:+.3f})")
        if shadow is not None:                                  # EMA는 부가 표시
            backup = _swap_in_ema()
            me = evaluate(model, va, 50, device)
            _swap_out(backup)
            m["val_ema"] = me["val_loss"]; line += f"  [ema {me['val_loss']:.4f}]"
        if "bpb" in m: line += f"  bpb {m['bpb']:.3f}"
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
        if sched == "decay":                    # 이미 학습된 plateau라 완전 삼진 유지
            anneal = 1.0
        else:
            a0 = warm / steps + 0.05
            anneal = min(1.0, max(0.0, (s / steps - a0) / max(0.60 - a0, 1e-6)))
        model.set_anneal(anneal)
        f = _lr_factor(s, warm, steps, sched)
        for g, b in zip(opt.param_groups, base_lrs):
            g["lr"] = b * f

        # Skip-Forward / Dynamic KD: 이 스텝에서 교사 forward를 수행할지 결정(P017).
        #   kd_every=1 → 매 스텝(기존). kd_every=K → K스텝마다 1회(교사 연산 1/K).
        #   kd_dynamic → 간격을 1→K 로 선형 증가(초반 촘촘한 KD, 후반 성김).
        kd_this = teacher is not None
        if teacher is not None and kd_every > 1:
            cur_every = (max(1, round(1 + (kd_every - 1) * s / steps))
                         if kd_dynamic else kd_every)
            kd_this = (s % cur_every == 0)
        if kd_this and teacher is not None:
            n_kd_fwd += 1

        model.train()
        tot = 0.0
        for _ in range(accum):
            x, y = tr()
            if _cudagraph_step is not None:
                _cudagraph_step()
            with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
                logits = model(x)
                ce = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1))
                if kd_reader is not None:               # 오프라인 KD(캐시 top-k)
                    from .kd_cache import kd_cache_loss
                    tv, ti = kd_reader.next(device)
                    kl = kd_cache_loss(logits, tv, ti, cfg.vocab_size, kd_temp)
                    loss = ((1 - kd_alpha) * ce + kd_alpha * kl) / accum
                elif teacher is not None and kd_this:   # 온라인 KD(교사 forward, skip-forward 반영)
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
        if ema > 0 and s >= ema_start_step:     # P1: 감쇠 구간의 좋은 가중치만 평균
            with torch.no_grad():
                if shadow is None:
                    shadow = [p.detach().clone() for p in params]
                else:
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
        if (s + 1) in snap_steps:               # 토큰 마크 스냅샷(plateau 분기 소스)
            snap = CKPT / f"{name}_snap{snap_steps[s + 1]}.pt"
            torch.save({"model": model.state_dict(), "cfg": cfg.__dict__, "step": s + 1}, snap)
            print(f"       [snapshot] {snap_steps[s + 1]} 토큰 지점 저장 -> {snap.name}")

    final = evaluate(model, va, 100, device, bytes_per_token=bpt); final["ema"] = False
    if shadow is not None:
        backup = _swap_in_ema(); fe = evaluate(model, va, 100, device); _swap_out(backup)
        final["val_ema"], final["ppl_ema"] = fe["val_loss"], fe["ppl"]
    n_par = sum(p.numel() for p in model.parameters())
    res = {"arch": arch, "preset": preset, "data": data, "params": n_par, "steps": steps,
           "lr": lr, "seq": seq,
           "tokens": steps * eff, "final": final, "best_val": best_val, "best_step": best_step,
           "history": hist, "grad_max": gmax, "grad_peak_warmup": gpeak, "n_skip": n_skip,
           "sched": sched, "ema": ema, "kd": bool(kd), "init_from": bool(init_from),
           "kd_every": kd_every, "kd_dynamic": bool(kd_dynamic), "kd_fwd_steps": n_kd_fwd,
           "lora_rank": lora_rank, "wall_sec": time.time() - t0,
           "sparse34": bool(sparse34), "bpw": 1.25 if sparse34 else 1.95}
    res["tag"] = name
    (LOGS / f"{name}.json").write_text(json.dumps(res, indent=2))
    kd_note = ""
    if teacher is not None and kd_every > 1:
        kd_note = f", KD forward {n_kd_fwd}/{steps}스텝(≈{n_kd_fwd/max(steps,1)*100:.0f}%)"
    print(f"\n[{label}] 최종 val_loss {final['val_loss']:.4f}  ppl {final['ppl']:.2f}  "
          f"best {best_val:.4f}@{best_step}  ({n_par/1e6:.1f}M, {(time.time()-t0)/60:.1f}분, skip {n_skip}{kd_note})")
    return res
