#!/usr/bin/env python3
"""P028 단계1 — **공통 원문 bpb**. 데이터셋 간 비교를 처음으로 성립시킨다.

★왜 필요한가 (결과 009 §판정, 결과 011)
   `ko-en` 과 `ko-edu-en` 은 **토크나이저도 val 셋도 다르다.** 그래서 두 모델의 val_loss 나
   bpb 를 나란히 놓는 것은 **무효**다. 결과 009 가 "관측은 열세지만 판정 불가" 로 끝난 이유가
   이것이고, 그 뒤로 데이터 계열 실험 전체가 여기 막혀 있었다.

★해법 — **어느 학습 코퍼스에도 없는 공통 원문**을 두 모델에 똑같이 통과시킨다
   bpb = loss / ln2 / bytes_per_token 이고, **같은 원문·같은 바이트 수**라면
   토크나이저가 달라도 분모가 같아진다. 즉 **bpb 는 토크나이저 무관**이 된다.

   원문 = **SQuAD v2 의 `context`** (`datasets/squad/train-v2.0.json`, 로컬 보유).
   고유 context 19,029개 / 14.0MB / 평균 736자. 영문 위키 산문이고 우리 `ko-en`·`ko-edu-en`
   어디에도 들어 있지 않다. 근거·대안 검토는 `docs/methods/07_corpus_selection.md` §3.

★★반드시 함께 읽을 한계
   1. **영문 전용이다.** 한국어 공통 원문은 여전히 없다. 이 스크립트가 재는 것은
      "영문 산문에 대한 압축률" 이지 모델 전체 품질이 아니다.
   2. 모델마다 **토크나이저가 다르므로 토큰 수가 다르다.** 그래서 손실을 그대로 비교하면
      안 되고 **반드시 bpb 로 환산**해야 한다. 이 스크립트가 그걸 강제한다.
   3. SQuAD context 는 **영문 위키**다. `ko-en` 은 영문 fineweb-edu 를 절반 썼고
      `ko-edu-en` 도 그렇다 — **도메인이 완전히 낯설지는 않다.** 그건 공정하다(둘 다 같은 조건).

사용법
  python scripts/common_bpb.py --models p6d t_kd_g8
  python scripts/common_bpb.py --models p6d --data ko-en --tokens 300M
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SQUAD = ROOT / "datasets" / "squad" / "train-v2.0.json"


def load_squad_contexts(path=SQUAD, limit=None):
    """고유 `context` 만 뽑아 순서를 고정해 돌려준다(문서 중복 제거).

    ★순서를 고정하는 이유: 이 텍스트가 **모든 모델에 동일**해야 비교가 성립한다.
    set 을 그대로 쓰면 파이썬 해시 시드에 따라 순서가 달라질 수 있으므로 정렬한다.
    """
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    seen, out = set(), []
    for art in d["data"]:
        for para in art["paragraphs"]:
            c = para["context"]
            if c not in seen:
                seen.add(c)
                out.append(c)
    out.sort()                       # ★결정성
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser(description="P028 단계1 공통 원문 bpb")
    ap.add_argument("--models", nargs="+", required=True,
                    help="태그 목록. 서로 **다른 데이터셋으로 학습된 모델**을 넣는 것이 요점이다")
    ap.add_argument("--data", nargs="+", default=None,
                    help="모델별 데이터셋(토크나이저 선택용). 미지정이면 --data-default 를 전부 적용")
    ap.add_argument("--data-default", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--arch", nargs="+", default=None, help="모델별 dense/tied. 미지정이면 태그로 추정")
    ap.add_argument("--max-docs", type=int, default=4000,
                    help="쓸 context 개수. 기본 4000 ≈ 3MB ≈ val 의 2배. 0 이면 전부")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--micro-bs", type=int, default=8)
    # ★★2026-08-26 (결과 053 §단계1) — **어휘가 커지면 여기가 먼저 죽는다.**
    #   `logits.reshape(-1, V).float()` 는 `micro_bs × seq × V × 4B` 를 **한 번에** 잡는다.
    #   V=151,936 · mb8 · seq1024 이면 **4.64 GiB 단일 할당**이고 두 번째 모델에서 OOM 했다.
    #   🚫**M=8192 무릎은 어휘 32,768 기준의 수이지 상수가 아니다** — 우리가 결과 053 에
    #   그렇게 적어 놓고 이 도구에는 반영하지 않았다.
    #   ★해법은 학습 경로와 같다(P071 로 등가성이 검증된 형태): **어휘가 아니라 행을 쪼갠다.**
    ap.add_argument("--ce-chunk", type=int, default=0, metavar="행수",
                    help="CE 를 이 행 수로 나눠 계산(0=끄기, 종전과 비트 동일). "
                         "어휘가 크면 4096 정도를 준다")
    ap.add_argument("--device", default=None)
    # ★★2026-09-02 E21 — SQuAD **train**-v2.0 의 8.7%(348/4,000)가 우리 학습 스트림과
    #   축자 겹친다(로그 068 [4/4], 평균 히트율 2.92% · 최대 100%).
    #   🚫**기본값은 종전과 비트 동일**이다 — 과거 bpb 전부가 이 4,000개 위에서 나왔고
    #   조용히 바꾸면 그 수들과 비교가 끊긴다. 켤 때만 제외한다.
    ap.add_argument("--drop-contaminated", action="store_true",
                    help="🚫**미구현**(2026-09-03 결과 053 §12.3 에서 무동작 확인). "
                         "선결 = 오염 348개의 **문서 인덱스 목록**을 파일로 저장하는 것 "
                         "— 로그 068 [4/4] 가 세기만 하고 목록을 안 남겼다. "
                         "지금 주면 **조용히 아무 일도 안 한다**")
    ap.add_argument("--tokenizer-hf", nargs="*", default=None, metavar="TAG=폴더",
                    help="★(P067) 태그별 외부 토크나이저. 예: mC_q3teach=HF/models--Qwen3-0.6B-Base "
                         "⚠️`run100m.py train` 의 같은 이름 플래그는 **맨 폴더**를 받는다 — 규약이 다르다")
    a = ap.parse_args()

    # ★★2026-09-02 E14 — **같은 플래그 이름이 두 도구에서 다른 규약**이다(함정 28).
    #   `run100m.py train --tokenizer-hf <폴더>`  (맨 폴더 하나)
    #   `common_bpb.py   --tokenizer-hf TAG=<폴더>` (태그마다 하나)
    #   배치가 학습 형태를 복사해 넣었고, 종전에는 `assert` 가 **폴더 이름만 되풀이**해서
    #   무엇이 틀렸는지 안 알려 줬다. 그래서 **8.8시간 런의 헤드라인 비교가 통째로 날아갔다.**
    #   -> 거절은 유지하되(추측해서 붙이면 조용히 틀린 토크나이저로 잰다),
    #      **고쳐 쓸 문장을 그대로 인쇄**한다.
    _tokmap = {}
    for spec in (a.tokenizer_hf or []):
        if "=" not in spec:
            print("[!] ★--tokenizer-hf 는 **TAG=폴더** 형식이다. 받은 것: " + spec)
            print("    ⚠️`run100m.py train` 의 같은 이름 플래그는 맨 폴더를 받는다 —")
            print("      **두 도구의 규약이 다르다**(함정 28). 학습 명령을 복사하면 여기서 죽는다.")
            _guess = (a.models[0] if a.models else "TAG")
            print("    이렇게 쓴다:")
            print(f"      --models {' '.join(a.models)} --tokenizer-hf {_guess}={spec}")
            print("    🚫추측해서 붙이지 않는다 — 틀린 토크나이저로 재면 bpb 가 조용히 무효가 된다.")
            return 2
        k, v = spec.split("=", 1)
        _tokmap[k.strip()] = v.strip()

    import numpy as np
    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm import paths
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model

    if not SQUAD.exists():
        print(f"[!] SQuAD 원문이 없다: {SQUAD}")
        return 2

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    docs = load_squad_contexts(limit=(a.max_docs or None))
    text = "\n\n".join(docs)
    n_bytes = len(text.encode("utf-8"))

    print("#" * 92)
    print("  P028 단계1 — 공통 원문 bpb (SQuAD v2 context)")
    print("#" * 92)
    print(f"  device={dev}  문서 {len(docs):,}개  **{n_bytes/1e6:.2f} MB**  seq={a.seq}")
    print("  ★같은 원문·같은 바이트에 서로 다른 토크나이저의 모델을 통과시킨다.")
    print("    bpb = loss / ln2 / (bytes/token) 이므로 **토크나이저가 달라도 비교가 성립**한다.")
    print("  ⚠️ 영문 전용이다. 한국어 공통 원문은 아직 없다(07_corpus_selection §3).")
    print("  ⚠️★**이 4,000개 중 8.7%(348개)가 우리 학습 스트림과 축자 겹친다**"
          "(로그 068 [4/4]).")
    print("     모든 후보 모델이 **같은 스트림**으로 학습됐으므로 서로 간 비교는 유효하지만,")
    print("     🚫**절대 bpb 는 낙관 쪽으로 치우쳐 있다** — 외부 모델과 비교할 때 특히 그렇다.")

    datas = a.data if a.data else [a.data_default] * len(a.models)
    if len(datas) == 1 and len(a.models) > 1:
        datas = datas * len(a.models)
    assert len(datas) == len(a.models), "--data 개수가 --models 와 다르다"
    archs = a.arch if a.arch else [
        "dense" if t.startswith(("p6d", "dense", "p12d")) else "tied" for t in a.models]

    rows = []
    for tag, data, arch in zip(a.models, datas, archs):
        ck = paths.resolve_ckpt(a.preset, data, a.tokens, tag)
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        # ★★P067(2026-08-22) — 외부 토크나이저로 학습한 체크포인트는 **그 토크나이저**로 재야 한다.
        #   `--tokenizer-hf TAG=<폴더>` 로 태그별 지정. 없으면 종전(우리 BPE) = 비트 동일.
        #   ⚠️★**common bpb 는 P067 런을 기존 런과 비교하는 유일한 유효 경로**다 —
        #   여기서 토크나이저를 틀리면 그 경로마저 무효가 된다.
        _hf = _tokmap.get(tag)
        if _hf:
            from tinylm.hf_spec import load_hf_tokenizer
            tok, _td = load_hf_tokenizer(_hf)
            print(f"  [P067] {tag}: 외부 토크나이저 {_td}")
        else:
            tok = load_tokenizer(data)
        ids = tok.encode(text).ids
        n_tok = len(ids)
        bpt = n_bytes / max(n_tok, 1)            # ★이 모델 토크나이저의 bytes/token

        # ── ★E22 게이트(2026-09-03) — **모델을 로드하기 전에** CE 메모리를 계산한다.
        #   종전 경로는 `F.cross_entropy(l2.float(), y1)` 로 어휘 전체 위에
        #   **fp32 사본을 한 번에** 만든다: micro_bs x seq x 어휘 x 4B.
        #   2026-09-03 에 gemma 어휘 262,144 x (8 x 1024) x 4B = **정확히 8.00 GiB**
        #   를 요구해 OOM 으로 죽었다. 학습 400.3분이 끝난 **직후**였다.
        #   ★그리고 이것은 회귀다 — 단계1d 가 `--micro-bs 2 --ce-chunk 4096` 으로
        #   같은 함정을 이미 넘었는데 그 두 플래그가 새 배치로 안 옮겨왔다.
        try:                                   # ★게이트가 게이트 대상을 깨면 안 된다
            _V = int(tok.get_vocab_size())
        except Exception:                      # noqa: BLE001
            try:
                _V = len(tok.get_vocab())
            except Exception:                  # noqa: BLE001
                _V = 0                         # 모르면 막지 않는다(경고만 건너뛴다)
        _rows_ce = a.ce_chunk if a.ce_chunk and a.ce_chunk > 0 else a.micro_bs * a.seq
        _fp32_gb = _rows_ce * _V * 4 / 1e9
        _logit_gb = a.micro_bs * a.seq * _V * 2 / 1e9      # bf16 logits 는 청킹과 무관
        _need = _fp32_gb + _logit_gb
        if _V:
            print(f"     [E22] 어휘 {_V:,} · CE fp32 사본 {_fp32_gb:.2f} GB "
                  f"+ logits(bf16) {_logit_gb:.2f} GB = **{_need:.2f} GB**")
        if dev == "cuda" and _V and _need > 6.0:
            print(f"\n  🚫★**CE 메모리가 {_need:.2f} GB 다 — 이대로면 OOM 이다**(E22).")
            print(f"     어휘가 {_V:,} 라 fp32 사본이 어휘에 정비례한다.")
            print(f"     ★`--ce-chunk` 는 fp32 사본만 나눈다 — `logits`(bf16, "
                  f"{_logit_gb:.2f} GB)는 **`--micro-bs` 로만** 줄어든다.")
            print("     고쳐 쓸 명령줄:")
            _fix = " ".join(f"--tokenizer-hf {k}={v}" for k, v in _tokmap.items())
            print(f"       python scripts/common_bpb.py --preset {a.preset} "
                  f"--models {' '.join(a.models)} --micro-bs 2 --ce-chunk 1024 {_fix}")
            print("     (단계1d 정본은 `--micro-bs 2 --ce-chunk 4096` 이었다)")
            return 2

        model, cfg, _ = load_model(arch=arch, ckpt_path=str(ck), device=dev)
        was = cfg.quant_anneal
        model.set_anneal(1.0); model.eval(); model.freeze_quant()

        arr = np.array(ids, dtype=np.int64)
        n_crop = (len(arr) - 1) // a.seq
        tot, cnt = 0.0, 0
        with torch.no_grad():
            for i in range(0, n_crop, a.micro_bs):
                chunk = [arr[j*a.seq:(j+1)*a.seq + 1] for j in range(i, min(i + a.micro_bs, n_crop))]
                t = torch.from_numpy(np.stack(chunk)).to(dev)
                x, y = t[:, :-1], t[:, 1:]
                with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                    logits = model(x)
                l2, y1 = logits.reshape(-1, logits.size(-1)), y.reshape(-1)
                C = int(a.ce_chunk or 0)
                if C <= 0 or C >= l2.shape[0]:
                    l = F.cross_entropy(l2.float(), y1)      # ★종전 경로 = 비트 동일
                else:
                    # ⚠️`reduction="mean"` 의 분모는 N 이 아니라 **무시되지 않은 타깃 수**다.
                    #   우리는 ignore_index 를 안 쓰므로 sum/N 이 mean 과 같다(P071 E-4).
                    ssum = 0.0
                    for i0 in range(0, l2.shape[0], C):
                        ssum += float(F.cross_entropy(
                            l2[i0:i0 + C].float(), y1[i0:i0 + C], reduction="sum"))
                    l = ssum / l2.shape[0]
                tot += float(l) * y.numel(); cnt += y.numel()
        model.clear_quant(); model.train(); model.set_anneal(was)
        loss = tot / cnt
        bpb = loss / math.log(2) / bpt
        rows.append((tag, data, n_tok, bpt, loss, bpb))
        print(f"\n  ── {tag} ({data}, {arch})")
        print(f"     토큰 {n_tok:,}  bytes/token {bpt:.4f}  손실 {loss:.4f}  **bpb {bpb:.4f}**")
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    if len(rows) < 2:
        print("\n  비교할 모델이 2개 미만이다. 데이터셋이 다른 모델을 최소 둘 넣어야 의미가 있다.")
        return 0 if rows else 2

    print("\n" + "=" * 92)
    print("  ★공통 원문 bpb — 이것이 데이터셋 간 비교로 유효한 유일한 수치다")
    print("=" * 92)
    print(f"  {'모델':<18}{'데이터셋':<14}{'토큰수':>10}{'B/tok':>8}{'손실':>9}{'bpb':>9}")
    print("  " + "-" * 72)
    for tag, data, n_tok, bpt, loss, bpb in sorted(rows, key=lambda r: r[5]):
        print(f"  {tag:<18}{data:<14}{n_tok:>10,}{bpt:>8.3f}{loss:>9.4f}{bpb:>9.4f}")

    best = min(rows, key=lambda r: r[5])
    print(f"\n  최저 bpb = {best[0]} ({best[1]}) {best[5]:.4f}")

    # ★★2026-09-07 — **자를 실측했다**(결과 075 §15, P088 단계7). 종전에는 여기서
    #   *"0.024 nats 를 환산하면 대략 0.008"* 이라고 찍었는데 그 0.024 는 **폐기된 fallback**
    #   이었다. 🚫**빌린 자로 판정하면 검정력이 없는 시험을 돌린다**(결과 075 §14.2).
    #   ★정본은 `scripts/_rulers.py` 하나다 — 여기서 표를 다시 적지 않는다(함정 18).
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _rulers                                            # noqa: PLC0415
        _tags = {r[0] for r in rows}
        _hit = {t: v for t, v in _rulers.BPB_BY_SHAPE.items() if t in _tags}
        print(f"\n  ★쓸 자(공통 원문 bpb, 실측 2σ) — 보수값 **{_rulers.BPB:.5f}** "
              f"(전 계열 최대, 결과 075 §15)")
        if _hit:
            print("     이 호출에 해당하는 형상별 자: "
                  + " · ".join(f"{t} {v:.5f}" for t, v in sorted(_hit.items())))
        print(f"     ★환산 nats = bpb x {_rulers.BPB_TO_NATS} · "
              f"교호작용의 자는 x{_rulers.INTERACTION:.3f}")
        print(f"     🚫종전 인쇄값 {_rulers.BPB_LEGACY} 는 **폐기 fallback 0.024 의 환산치**다 — 인용 금지")
    except Exception as e:                                        # noqa: BLE001
        print(f"\n  ⚠️자를 못 읽었다({e}) — `scripts/_rulers.py` 를 직접 본다")

    print("""
  읽는 법
    · **bpb 만** 비교한다. '손실' 열은 토크나이저마다 토큰 수가 달라 **비교 불가**다.
      (일부러 함께 찍는다 — 둘이 다른 이야기를 한다는 것이 이 실험의 요점이다)
    · bpb 차이가 위에 인쇄된 **실측 자**보다 작으면 **서열을 매기지 않는다.**
    · 토큰 수가 크게 다르면 그 자체가 정보다 — 토크나이저가 이 원문을 얼마나 잘 압축하는가.

  한계
    · **영문 전용.** 한국어 쪽 결론은 이 실험으로 나오지 않는다.
    · SQuAD context 는 영문 위키다. 두 모델 다 영문을 절반 학습했으므로 조건은 공정하지만,
      **한국어 능력은 전혀 반영되지 않는다.**
    · 문서를 `\\n\\n` 로 이어붙여 하나의 스트림으로 만든다 — 문서 경계에서 컨텍스트가 섞인다.
      모든 모델에 동일하게 적용되므로 비교에는 영향이 없다.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
