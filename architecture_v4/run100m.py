#!/usr/bin/env python3
"""
run100m.py — 검증용 100M급 모델의 데이터 준비 / 학습 / 평가 / 비교 파이프라인

이 실험의 목적은 절대 점수가 아니라 **동일 조건에서 dense와 tied의 차이**를 재는 것이다.
그래서 데이터를 먼저 바이너리로 굳혀놓고 두 런이 정확히 같은 토큰을 같은 순서로 보게 한다.

  # 1) 데이터 준비 (한 번만)
  python run100m.py prepare --data ko-en --tokens 300M

  # 2) 기준선 학습
  python run100m.py train --arch dense

  # 3) 개선판 학습
  python run100m.py train --arch tied

  # 4) 비교
  python run100m.py compare

전체 자동 실행:
  python run100m.py all --data ko-en --tokens 300M

네트워크 없이 동작 확인만:
  python run100m.py all --data synthetic --tokens 2M --steps 30
"""
from __future__ import annotations

import argparse, json, math, os, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from tied_mlp_transformer import TMTConfig, TiedMLPTransformer, dense_baseline

ROOT = Path(os.environ.get("RUN100M_DIR", "./run100m"))
DATA, CKPT, LOGS = ROOT / "data", ROOT / "ckpt", ROOT / "logs"
VOCAB = 32768


# ===========================================================================
# 데이터
# ===========================================================================

DATASETS = {
    # 이름: [(hf_id, config, split, text_key, 혼합 비율), ...]
    "ko-en": [("wikimedia/wikipedia", "20231101.ko", "train", "text", 0.5),
              ("HuggingFaceFW/fineweb-edu", "sample-10BT", "train", "text", 0.5)],
    "ko":    [("wikimedia/wikipedia", "20231101.ko", "train", "text", 1.0)],
    "en":    [("Salesforce/wikitext", "wikitext-103-raw-v1", "train", "text", 1.0)],
}


def _stream(name):
    """혼합 비율에 따라 여러 데이터셋에서 번갈아 텍스트를 뽑는다."""
    from datasets import load_dataset
    specs = DATASETS[name]
    iters, ratios = [], []
    for hf_id, cfg, split, key, r in specs:
        ds = load_dataset(hf_id, cfg, split=split, streaming=True)
        iters.append((iter(ds), key)); ratios.append(r)
    rng = np.random.default_rng(0)
    p = np.array(ratios) / sum(ratios)
    while True:
        i = rng.choice(len(iters), p=p)
        it, key = iters[i]
        try:
            t = next(it)[key]
        except StopIteration:
            continue
        if t and len(t) > 64:
            yield t


def build_tokenizer(name, vocab_size=VOCAB):
    """캐시가 있으면 로드, 없으면 코퍼스 표본으로 ByteLevel BPE를 학습한다."""
    from tokenizers import ByteLevelBPETokenizer
    path = DATA / f"tok-{name}-{vocab_size}.json"
    if path.exists():
        from tokenizers import Tokenizer
        print(f"[tok] 캐시 사용 {path}")
        return Tokenizer.from_file(str(path))

    print(f"[tok] {vocab_size} BPE 학습 중 (표본 20만 문서)...")
    tok = ByteLevelBPETokenizer()
    src = _stream(name)
    def sample():
        for i, t in enumerate(src):
            if i >= 200_000:
                break
            yield t
    tok.train_from_iterator(sample(), vocab_size=vocab_size, min_frequency=2,
                            special_tokens=["<pad>", "<bos>", "<eos>"])
    DATA.mkdir(parents=True, exist_ok=True)
    tok.save(str(path))
    print(f"[tok] 저장 {path}")
    return tok


def prepare(name, n_tokens, val_frac=0.005):
    DATA.mkdir(parents=True, exist_ok=True)
    meta_p = DATA / "meta.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text())
        if meta["data"] == name and meta["tokens"] >= n_tokens:
            print(f"[data] 기존 바이너리 재사용: {meta['tokens']/1e6:.1f}M 토큰 ({name})")
            return meta

    if name == "synthetic":
        print(f"[data] 합성 토큰 {n_tokens/1e6:.1f}M 생성 (동작 확인용)")
        rng = np.random.default_rng(0)
        # 순수 랜덤이면 loss가 안 떨어져 비교가 무의미하므로 학습 가능한 구조를 넣는다:
        # 짧은 문구 사전에서 문구를 무작위로 이어붙인다 -> n-gram 학습이 가능해짐
        vocab_eff = min(VOCAB, 4096)
        phrases = [rng.integers(0, vocab_eff, rng.integers(3, 12)) for _ in range(50_000)]
        out, n = [], 0
        while n < n_tokens:
            ph = phrases[rng.integers(len(phrases))]
            out.append(ph); n += len(ph)
        arr = np.concatenate(out)[:n_tokens].astype(np.uint16)
        tok = None
    else:
        tok = build_tokenizer(name)
        eos = tok.token_to_id("<eos>") or 2
        buf, total = [], 0
        t0 = time.time()
        for text in _stream(name):
            ids = tok.encode(text).ids
            buf.append(np.array(ids + [eos], dtype=np.uint16))
            total += len(ids) + 1
            if total >= n_tokens:
                break
            if total % 5_000_000 < 2000:
                print(f"  {total/1e6:>6.1f}M / {n_tokens/1e6:.0f}M  "
                      f"({total/max(time.time()-t0,1e-9)/1e3:.0f}K tok/s)")
        arr = np.concatenate(buf)[:n_tokens]

    n_val = int(len(arr) * val_frac)
    arr[:-n_val].tofile(DATA / "train.bin")
    arr[-n_val:].tofile(DATA / "val.bin")
    meta = {"data": name, "tokens": int(len(arr)), "vocab": VOCAB,
            "train": int(len(arr) - n_val), "val": int(n_val)}
    meta_p.write_text(json.dumps(meta, indent=2))
    print(f"[data] train {meta['train']/1e6:.1f}M / val {meta['val']/1e3:.0f}K 토큰 저장")
    return meta


class Loader:
    """memmap에서 무작위 크롭. 시드가 같으면 두 런이 정확히 같은 배치를 본다."""

    def __init__(self, split, bs, seq, device, seed=1234):
        self.d = np.memmap(DATA / f"{split}.bin", dtype=np.uint16, mode="r")
        self.bs, self.seq, self.device = bs, seq, device
        self.rng = np.random.default_rng(seed)

    def __call__(self):
        ix = self.rng.integers(0, len(self.d) - self.seq - 1, self.bs)
        x = np.stack([self.d[i:i+self.seq+1] for i in ix]).astype(np.int64)
        t = torch.from_numpy(x)
        if self.device == "cuda":
            t = t.pin_memory().to("cuda", non_blocking=True)
        return t[:, :-1], t[:, 1:]


# ===========================================================================
# 모델 설정
# ===========================================================================

def make_config(arch, seq, tiny=False, ckpt=True):
    if tiny:   # 파이프라인 동작 확인용. 아키텍처 비율은 그대로 유지한다.
        cfg = TMTConfig(vocab_size=VOCAB, dim=256, ffn_dim=512, n_q_heads=4, n_kv_heads=1,
                        emb_rank=64, n_prelude=1, n_middle=4, n_coda=1,
                        mlp_group=2, cla_group=2, n_modes=1, mode_rank=0,
                        micro_group=128, max_seq_len=seq, grad_checkpoint=ckpt)
    else:
        cfg = TMTConfig(
            vocab_size=VOCAB, dim=768, ffn_dim=2048, n_q_heads=12, n_kv_heads=3,
            emb_rank=256, n_prelude=2, n_middle=16, n_coda=2,
            mlp_group=4, cla_group=2, n_modes=1, mode_rank=0,
            micro_group=128, max_seq_len=seq, grad_checkpoint=ckpt)
    return cfg if arch == "tied" else dense_baseline(cfg)


# ===========================================================================
# 평가
# ===========================================================================

@torch.no_grad()
def evaluate(model, loader, iters, device, bytes_per_token=None):
    """반드시 배포 상태(완전 삼진)에서 잰다."""
    was, model.cfg.quant_anneal = model.cfg.quant_anneal, 1.0
    model.eval(); model.refresh_quant()
    tot = 0.0
    for _ in range(iters):
        x, y = loader()
        with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
            logits = model(x)
        tot += F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                               y.reshape(-1)).float().item()
    model.clear_quant(); model.train(); model.cfg.quant_anneal = was
    loss = tot / iters
    out = {"val_loss": loss, "ppl": math.exp(min(loss, 20))}
    if bytes_per_token:
        out["bpb"] = loss / math.log(2) / bytes_per_token
    return out


# ===========================================================================
# 학습
# ===========================================================================

def train(arch, steps, micro_bs, seq, accum, lr, eval_every, resume=False,
          tiny=False, ckpt=True, compile_=False):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(1337)
    CKPT.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)

    cfg = make_config(arch, seq, tiny, ckpt)
    model = TiedMLPTransformer(cfg).to(device)
    if compile_:
        print('[compile] torch.compile 첫 스텝은 수 분 걸릴 수 있습니다')
        model = torch.compile(model)
    print(model.report())
    eff = micro_bs * accum * seq
    print(f"[{arch}] device={device}  {steps}step x {eff/1e3:.0f}K tok = "
          f"{steps*eff/1e6:.0f}M 토큰\n")

    opt = torch.optim.AdamW(model.param_groups(lr), betas=(0.9, 0.95), eps=1e-8)
    base_lrs = [g["lr"] for g in opt.param_groups]
    warm = max(20, steps // 50)

    start = 0
    ck = CKPT / f"{arch}.pt"
    if resume and ck.exists():
        st = torch.load(ck, map_location=device)
        model.load_state_dict(st["model"]); opt.load_state_dict(st["opt"]); start = st["step"]
        print(f"[{arch}] step {start}에서 재개")

    tr = Loader("train", micro_bs, seq, device, seed=1234)
    va = Loader("val", micro_bs, seq, device, seed=99)
    hist, t0, gmax = [], time.time(), 0.0

    for s in range(start, steps):
        # 삼진 어닐링: warmup이 끝난 뒤 시작해 60% 지점에서 완료.
        # (앞 버전은 어닐 종료와 LR 피크가 겹쳐 그라디언트 스파이크를 유발했다)
        a0 = warm / steps + 0.05
        model.cfg.quant_anneal = min(1.0, max(0.0, (s / steps - a0) / max(0.60 - a0, 1e-6)))
        f = (s + 1) / warm if s < warm else \
            0.1 + 0.45 * (1 + math.cos(math.pi * (s - warm) / max(steps - warm, 1)))
        for g, b in zip(opt.param_groups, base_lrs):
            g["lr"] = b * f

        model.train()
        tot = 0.0
        for _ in range(accum):
            x, y = tr()
            with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
                logits = model(x)
                loss = F.cross_entropy(logits.reshape(-1, VOCAB), y.reshape(-1)) / accum
            loss.backward()
            tot += loss.item()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        gmax = max(gmax, float(gn))
        opt.step(); opt.zero_grad(set_to_none=True)
        model.clear_quant()            # _wq가 붙잡은 그래프 해제

        if s % 10 == 0 or s == steps - 1:
            el = time.time() - t0
            print(f"  step {s:>5}/{steps}  loss {tot:.4f}  |g| {gn:.2f}  "
                  f"anneal {model.cfg.quant_anneal:.2f}  lr {opt.param_groups[1]['lr']:.2e}  "
                  f"{el/(s-start+1)*1000:.0f} ms/step")
        if (s + 1) % eval_every == 0 or s == steps - 1:
            m = evaluate(model, va, 20, device)
            m.update(step=s + 1, train_loss=tot)
            hist.append(m)
            print(f"    >> val_loss {m['val_loss']:.4f}  ppl {m['ppl']:.2f}")
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(),
                        "step": s + 1, "cfg": cfg.__dict__}, ck)

    final = evaluate(model, va, 100, device)
    n_par = sum(p.numel() for p in model.parameters())
    res = {"arch": arch, "params": n_par, "steps": steps,
           "tokens": steps * eff, "final": final, "history": hist, "grad_max": gmax,
           "wall_sec": time.time() - t0}
    (LOGS / f"{arch}.json").write_text(json.dumps(res, indent=2))
    print(f"\n[{arch}] 최종 val_loss {final['val_loss']:.4f}  ppl {final['ppl']:.2f}  "
          f"({n_par/1e6:.1f}M 파라미터, {(time.time()-t0)/60:.1f}분)")
    return res


# ===========================================================================
# 비교
# ===========================================================================

def compare():
    out = {}
    for a in ("dense", "tied"):
        p = LOGS / f"{a}.json"
        if not p.exists():
            print(f"[compare] {p} 없음. 먼저 학습하세요."); return
        out[a] = json.loads(p.read_text())
    d, t = out["dense"], out["tied"]
    MB = lambda n: n * 1.95 / 8 / 1024**2
    dl, tl = d["final"]["val_loss"], t["final"]["val_loss"]

    print("=" * 68)
    print("  dense 기준선 vs tied 개선판   (동일 토큰·동일 시드)")
    print("=" * 68)
    print(f"  {'':<20}{'dense':>14}{'tied':>14}{'차이':>14}")
    print("  " + "-" * 62)
    print(f"  {'파라미터':<20}{d['params']/1e6:>13.1f}M{t['params']/1e6:>13.1f}M"
          f"{d['params']/t['params']:>13.2f}x")
    print(f"  {'배포 메모리':<20}{MB(d['params']):>12.1f}MB{MB(t['params']):>12.1f}MB"
          f"{MB(d['params'])/MB(t['params']):>13.2f}x")
    print(f"  {'val loss':<20}{dl:>14.4f}{tl:>14.4f}{tl-dl:>+14.4f}")
    print(f"  {'perplexity':<20}{d['final']['ppl']:>14.2f}{t['final']['ppl']:>14.2f}"
          f"{t['final']['ppl']/d['final']['ppl']:>13.2f}x")
    print(f"  {'학습 시간(분)':<20}{d['wall_sec']/60:>14.1f}{t['wall_sec']/60:>14.1f}"
          f"{d['wall_sec']/t['wall_sec']:>13.2f}x")
    print("  " + "-" * 62)
    gap = tl - dl
    for a in ("dense", "tied"):
        if out[a].get("grad_max"):
            print(f"  {'최대 |g| ('+a+')':<20}{out[a]['grad_max']:>14.1f}"
                  f"{'  (>10이면 불안정)' if out[a]['grad_max'] > 10 else ''}")
    meta = json.loads((DATA / "meta.json").read_text()) if (DATA/"meta.json").exists() else {}
    if meta.get("data") == "synthetic":
        print(f"\n  손실 격차 {gap:+.4f}")
        print("  !! 합성 데이터는 품질 판정에 쓸 수 없습니다.")
        print("     반복 구절 코퍼스는 '순수 암기' 과제라 파라미터 수가 그대로 성능이 됩니다.")
        print("     타잉은 정의상 파라미터를 줄이므로 구조적으로 불리하게 나옵니다.")
        print("     (실측: 암기 가능한 데이터 격차 +0.118 -> 암기 불가능한 데이터 +0.000)")
        print("     이 실행은 '파이프라인이 도는가'만 확인하는 용도입니다.")
        print("=" * 68); return
    print(f"\n  손실 격차 {gap:+.4f}   (논문 기준 MLP g=4의 예상치는 +0.05 ~ +0.07)")
    if gap <= 0.07:
        print("  -> 예상 범위 안. g를 더 키우거나 어텐션 타잉을 시험해볼 만함.")
    elif gap <= 0.15:
        print("  -> 다소 큼. prelude/coda를 3+3으로 늘리거나 g=2로 낮춰볼 것.")
    else:
        print("  -> 과도함. 삼진 어닐링 스케줄과 LR 1/sqrt(g) 보정부터 점검할 것.")
    print("=" * 68)


# ===========================================================================

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["prepare", "train", "eval", "compare", "all"])
    p.add_argument("--arch", choices=["dense", "tied"], default="tied")
    p.add_argument("--data", default="ko-en", choices=list(DATASETS) + ["synthetic"])
    p.add_argument("--tokens", default="300M")
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--micro-bs", type=int, default=8)
    p.add_argument("--seq", type=int, default=1024)
    p.add_argument("--accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--eval-every", type=int, default=250)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--tiny", action="store_true", help="파이프라인 동작 확인용 축소 모델")
    p.add_argument("--no-ckpt", action="store_true",
                   help="gradient checkpointing 끄기. VRAM 여유 있으면 ~30%% 빠름")
    p.add_argument("--compile", action="store_true", help="torch.compile 사용")
    a = p.parse_args()

    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))

    if a.cmd == "prepare":
        prepare(a.data, n_tok)
    elif a.cmd == "train":
        prepare(a.data, n_tok)
        train(a.arch, a.steps, a.micro_bs, a.seq, a.accum, a.lr, a.eval_every, a.resume,
              a.tiny, not a.no_ckpt, a.compile)
    elif a.cmd == "eval":
        device = "cuda" if torch.cuda.is_available() else "cpu"
        cfg = make_config(a.arch, a.seq, a.tiny)
        m = TiedMLPTransformer(cfg).to(device)
        m.load_state_dict(torch.load(CKPT / f"{a.arch}.pt", map_location=device)["model"])
        print(m.report())
        print(evaluate(m, Loader("val", a.micro_bs, a.seq, device, seed=99), 100, device))
    elif a.cmd == "compare":
        compare()
    elif a.cmd == "all":
        prepare(a.data, n_tok)
        for arch in ("dense", "tied"):
            print("\n" + "#" * 68 + f"\n#  {arch}\n" + "#" * 68)
            train(arch, a.steps, a.micro_bs, a.seq, a.accum, a.lr, a.eval_every, a.resume,
                  a.tiny, not a.no_ckpt, a.compile)
        print(); compare()


if __name__ == "__main__":
    main()
