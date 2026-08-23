#!/usr/bin/env python3
"""★★P067 단계0-b — **외부 교사 경로가 실제로 도는가.** 학습 0.

## 왜 스모크가 아니라 이 도구인가 (함정 37 을 다른 방법으로 문다)

함정 37 은 *"필드가 기록된다 ≠ 그 경로가 실행된다"* 이고, 규약은 **새 축을 뚫으면 그 축을
켠 스모크 팔을 함께 넣는 것**이다. 🚫**그런데 P067 축은 스모크에 못 넣는다**:

| 스모크의 전제 | P067 이 깨는 것 |
|---|---|
| `--data synthetic` | ★**합성 데이터는 토큰화를 건너뛴다** — 외부 토크나이저 경로가 아예 안 돌아간다 |
| `--tiny` 프리셋 | 교사 어휘 262,144 와 학생 어휘가 **맞아야** 하므로 tiny 임베딩이 262K 가 된다 |
| 수 분 | 실제 코퍼스 토큰화가 필요하다 |

→ ★**대신 이 도구가 같은 일을 한다**: 교사 로드 · 어휘 일치 · **실제 forward 1회** ·
**로짓 dtype** · 토크나이저 왕복. **그 경로가 실제로 도는 것을 눈으로 확인**한다.

## 성공 기준값 (결과보다 먼저 인쇄한다 — 함정 34)

| # | 게이트 | 기준 |
|---|---|---|
| **T1** | 교사가 `AutoModelForCausalLM` 으로 로드되는가 | ★**로드된다.** 멀티모달이면 여기서 실패할 수 있다 |
| **T2** | 교사 config `vocab_size` == 토크나이저가 낼 수 있는 최대 id + 1 이하 | ★**초과 id 0개** |
| **T3** | forward 로짓 shape | ★**(B, T, vocab_size)** |
| **T4** | ★**로짓 dtype** | ★**교사 config 의 dtype 그대로**(보통 bf16). fp32 승격은 `_kd_kl` 이 청크 안에서 한다(2026-08-23 정정) |
| **T5** | 토크나이저 왕복 | ★**한국어·영어 표본에서 decode(encode(x)) == x** |
| **T6** | 토큰 id 최대값 | ★**65,536 초과면 캐시 dtype 이 uint32 여야 한다**(안 그러면 조용히 wrap) |

사용법
    python scripts/diag_p067_teacher.py --teacher HF/models--google--gemma-3-270m
    python scripts/diag_p067_teacher.py --teacher HF/models--Qwen3-0.6B-Base --device cpu
    python scripts/diag_p067_teacher.py --spec-only        # 전 후보 config 만 (torch 0)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CANDIDATES = [
    "HF/models--Qwen3-0.6B-Base",
    "HF/models--google--gemma-3-270m",
    "HF/models--google--gemma-3-1b-pt",
    "HF/models--Qwen--Qwen3.5-0.8B-Base",
    "HF/models--google--gemma-4-E2B",
]

SAMPLES = [
    "한국어 문장을 토큰화하고 되돌린다.",
    "The quick brown fox jumps over the lazy dog.",
    "삼진 양자화(ternary quantization)는 가중치를 -1, 0, 1 로 만든다.",
]


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def do_spec():
    from tinylm.hf_spec import teacher_spec
    banner("교사 후보 실사 — config.json 만 읽는다. torch 0 · GPU 0", "#")
    print(f"  {'폴더':<34}{'arch':<32}{'텍스트전용':<11}{'L':>4}{'hidden':>8}"
          f"{'vocab':>9}{'dtype':>10}  tok.json")
    print("-" * 118)
    for c in CANDIDATES:
        try:
            s = teacher_spec(ROOT / c)
        except FileNotFoundError as e:                       # noqa: BLE001
            print(f"  {c:<34} 🚫 {e}")
            continue
        print(f"  {Path(c).name:<34}{str(s['arch']):<32}"
              f"{('YES' if s['text_only'] else '🚫NO'):<11}{s['n_layers']:>4}{s['hidden']:>8}"
              f"{s['vocab_size']:>9}{str(s['dtype']):>10}  {s['has_tokenizer']}")
    print("\n  ★**텍스트전용 NO 인 둘은 `*ForConditionalGeneration`** 이다 — 비전/오디오 탑이")
    print("    붙어 있다. `AutoModelForCausalLM` 이 텍스트 탑만 실을 수 있는지가 T1 이다.")
    print("  ★**우리 어휘 32,768 대비**: Qwen3 4.6배 · Gemma3 8.0배. 임베딩이 그만큼 커진다.")


def main():
    ap = argparse.ArgumentParser(description="P067 외부 교사 경로 게이트 (학습 0)")
    ap.add_argument("--teacher", default=None, help="HF 모델 폴더")
    ap.add_argument("--spec-only", action="store_true", help="config 만. torch 안 씀")
    ap.add_argument("--device", default=None)
    ap.add_argument("--dtype", choices=["bf16", "fp16", "fp32"], default="bf16")
    ap.add_argument("--seq", type=int, default=64)
    a = ap.parse_args()

    do_spec()
    if a.spec_only or not a.teacher:
        print("\n  ⚠️ `--teacher <폴더>` 를 주면 T1~T6 을 실제로 돌린다.")
        return 0

    banner("성공 기준값 — **결과보다 먼저 인쇄한다**(함정 34)", "#")
    print("  T1 교사 로드            기준: **성공**")
    print("  T2 어휘 초과 id         기준: **0개**")
    print("  T3 로짓 shape           기준: **(B, T, vocab_size)**")
    print("  T4 로짓 dtype           기준: ★**교사 config dtype 그대로**(보통 bf16). fp32 승격은 _kd_kl 이 청크 안에서")
    print("  T5 토크나이저 왕복       기준: **표본 3종 일치**")
    print("  T6 최대 토큰 id         기준: **65,536 초과면 캐시 dtype 이 uint32**")

    import torch
    from tinylm.train.hf_teacher import HFTeacher
    from tinylm.hf_spec import load_hf_tokenizer, teacher_spec

    fails = []
    tp = ROOT / a.teacher if not Path(a.teacher).is_absolute() else Path(a.teacher)
    sp = teacher_spec(tp)
    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")

    # T5/T6 먼저 — torch 없이도 되는 것부터
    banner("T5 / T6 — 토크나이저")
    tok, tdir = load_hf_tokenizer(tp)
    mx = 0
    for s in SAMPLES:
        enc = tok.encode(s)
        dec = tok.decode(enc.ids)
        mx = max(mx, max(enc.ids) if enc.ids else 0)
        ok = dec.strip() == s.strip()
        print(f"  {'✅' if ok else '🚫'} {len(enc.ids):>3}토큰  {s[:44]}")
        if not ok:
            print(f"      복원: {dec[:60]}")
            fails.append(f"T5 왕복 실패: {s[:30]}")
    print(f"\n  최대 토큰 id **{mx:,}**  / 교사 config vocab_size **{sp['vocab_size']:,}**")
    need32 = sp["vocab_size"] > 65536
    print(f"  T6 캐시 dtype 요구: **{'uint32' if need32 else 'uint16'}**  "
          f"{'⚠️★uint16 으로 쓰면 id 가 조용히 wrap 된다' if need32 else ''}")
    if mx >= sp["vocab_size"]:
        fails.append(f"T2 토큰 id {mx} >= vocab_size {sp['vocab_size']}")
        print(f"  🚫★**T2 실패** — 토크나이저가 교사 임베딩 밖의 id 를 낸다")
    else:
        print(f"  ✅ T2 초과 id 0개 (여유 {sp['vocab_size'] - mx - 1:,})")

    # T1/T3/T4
    banner(f"T1 / T3 / T4 — 교사 로드 + forward  (device={dev}, dtype={a.dtype})")
    try:
        t = HFTeacher(tp, sp["vocab_size"], dev, dtype=a.dtype)
    except Exception as e:                                   # noqa: BLE001
        print(f"  🚫★**T1 실패**: {type(e).__name__}: {str(e)[:200]}")
        print("  ★**멀티모달 모델이면 여기서 걸린다** — 그것도 결과다. "
              "순수 텍스트 후보(Qwen3-0.6B-Base / gemma-3-270m / gemma-3-1b-pt)로 가세요.")
        fails.append(f"T1 로드 실패: {type(e).__name__}")
        _verdict(fails)
        return 1
    print("  ✅ T1 로드 성공")

    x = torch.randint(0, sp["vocab_size"], (2, a.seq), dtype=torch.long, device=dev)
    lg = t(x)
    shape_ok = tuple(lg.shape) == (2, a.seq, sp["vocab_size"])
    print(f"  T3 로짓 shape {tuple(lg.shape)}  기대 {(2, a.seq, sp['vocab_size'])}  "
          f"{'✅' if shape_ok else '🚫'}")
    if not shape_ok:
        fails.append(f"T3 shape {tuple(lg.shape)}")
    # ★★2026-08-23 정정(함정 34) — 종전 기준 "fp32" 는 **내 수정보다 낡았다.**
    #   `HFTeacher.forward` 는 이제 **원 dtype 그대로** 돌려주고 fp32 승격은
    #   `_kd_kl` 이 **청크 안에서** 한다(결과 054: 통째 승격이 2.32 GiB 단일 할당이었다).
    #   → **bf16 이 정상**이다. 기준은 "교사 config 의 dtype 과 같은가" 로 바뀐다.
    _want = {"bfloat16": torch.bfloat16, "float16": torch.float16,
             "float32": torch.float32}.get(str(sp["dtype"]), torch.bfloat16)
    dt_ok = lg.dtype == _want
    print(f"  T4 로짓 dtype {lg.dtype}  기대 {_want}(교사 config 의 dtype)  "
          f"{'✅' if dt_ok else '🚫'}")
    print(f"     ★fp32 승격은 `_kd_kl` 이 **청크 단위로** 한다 — 여기서 올리면 "
          f"(B,T,V) fp32 단일 할당이 된다(결과 054)")
    if not dt_ok:
        fails.append(f"T4 dtype {lg.dtype} != 교사 config {sp['dtype']}")
    print(f"     로짓 범위 [{float(lg.min()):.2f}, {float(lg.max()):.2f}]  "
          f"평균 {float(lg.mean()):.4f}")
    print("     ⚠️★무작위 토큰을 넣었으므로 **로짓 값 자체는 의미 없다.** "
          "shape·dtype·NaN 만 본다.")
    if not torch.isfinite(lg).all():
        fails.append("로짓에 NaN/Inf 가 있다")
        print("  🚫★**로짓에 NaN/Inf** — dtype 이나 attn_implementation 문제다")

    # 메모리
    if dev == "cuda":
        print(f"\n  교사 VRAM: alloc {torch.cuda.memory_allocated()/2**30:.2f} GiB / "
              f"reserved {torch.cuda.memory_reserved()/2**30:.2f} GiB")
        print("  ⚠️★**KD 학습에서는 여기에 학생 + 어휘 전체 위의 KL 이 더해진다** — "
              "결과 038: 어휘 위 KD 손실이 +5.48 GiB 였다. **어휘가 8배면 그것도 커진다.**")
    _verdict(fails)
    return 1 if fails else 0


def _verdict(fails):
    banner("판정")
    if fails:
        for f in fails:
            print(f"  🚫 {f}")
        print(f"\n  총 {len(fails)}건 실패 — **P067 학습을 시작하지 마세요.**")
    else:
        print("  ✅ T1~T6 전 게이트 통과. **외부 교사 경로가 실제로 돈다.**")
        print("  ★다음: `run_P067_stage1_ext_teacher.bat`")
    print("=" * 96)


if __name__ == "__main__":
    sys.exit(main())
