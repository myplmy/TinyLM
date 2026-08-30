#!/usr/bin/env python3
"""P032 — **결정적 full-val + paired per-crop 비교**. 두 모델의 차이를 노이즈 아래로 밀어넣는다.

★왜 필요한가 (계획 P032 §1)
   결과 012 는 `mA_g4s34_k4` 3.7003 vs `p6d` 3.7045 = **-0.0042** 를 보고했다. 그런데
   σ = 0.012 이고 실무 분해능은 0.024 다. 이 차이를 **평균 비교**로 확정하려면 각 그룹
   49런 = 약 196시간이 필요하다 — 비현실적이다. 계획서가 그 경로를 폐기한 이유다.

★이 스크립트가 하는 두 가지 (둘 다 **학습을 다시 하지 않는다**)
   1. **결정적 full-val** — `evaluate()` 는 val 에서 50배치를 **랜덤 오프셋으로 복원추출**한다
      (1.5M 중 약 27%). 그래서 같은 체크포인트도 부를 때마다 값이 흔들린다. 여기서는
      `0, seq, 2*seq, ...` 로 **겹치지 않게 전부** 순회한다 → 같은 모델은 **항상 같은 값**.
      이것만으로 σ 의 eval 성분이 **0** 이 된다.
   2. **paired per-crop 비교** — 두 모델을 **같은 크롭 집합**에 통과시키고 크롭별 차이
      `d_i = loss_A(crop_i) - loss_B(crop_i)` 를 본다. "이 크롭이 원래 어려운가"는 두 모델에
      공통이므로 차이에서 **상쇄된다**. 독립 평균 비교보다 훨씬 작은 차이를 검출한다.

★★반드시 결과문서에 적을 한계 (계획 P032 §2.2)
   paired 비교는 **eval 노이즈만** 없앤다. **학습 재현 노이즈(시드)는 그대로 남는다.**
   따라서 이 스크립트가 확정할 수 있는 명제는
       "이 **두 체크포인트**는 다르다 / 같다"
   이고, 확정할 수 없는 명제는
       "이 **아키텍처**가 더 낫다"
   이다. 후자는 여전히 여러 시드가 필요하다. **이 구분을 흐리면 결과 015 의 실수
   (best 로 읽어 부호가 뒤집힌 사건)를 다른 형태로 반복하는 것이다.**

사용법
  python scripts/paired_eval.py --models mA_g4s34_k4 mC_g8_k4 p6d
  python scripts/paired_eval.py --models mA_g4s34_k4 p6d --seq 1024 --micro-bs 8
"""
from __future__ import annotations

import argparse
import itertools
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MODELS = ["mA_g4s34_k4", "mC_g8_k4", "p6d"]


def _arch_of(tag):
    return "dense" if tag.startswith(("p6d", "dense", "p12d")) else "tied"


def banner(s, ch="="):
    print("\n" + ch * 92)
    print(f"  {s}")
    print(ch * 92)


def full_val_losses(model, cfg, data_dir, seq, micro_bs, device):
    """val 전체를 **겹치지 않게 순차 순회**하며 크롭별 손실 벡터를 돌려준다.

    반환: (크롭별 손실 리스트, 사용 토큰 수). 같은 체크포인트면 **몇 번 불러도 같다.**
    """
    import numpy as np
    import torch
    import torch.nn.functional as F

    d = np.memmap(Path(data_dir) / "val.bin", dtype=np.uint16, mode="r")
    n_crop = (len(d) - 1) // seq
    starts = [i * seq for i in range(n_crop)]

    was = cfg.quant_anneal
    model.set_anneal(1.0)                 # 배포 상태(완전 삼진)
    model.eval()
    model.freeze_quant()
    out = []
    with torch.no_grad():
        for i in range(0, n_crop, micro_bs):
            chunk = starts[i:i + micro_bs]
            arr = np.stack([d[s:s + seq + 1] for s in chunk]).astype(np.int64)
            t = torch.from_numpy(arr).to(device)
            x, y = t[:, :-1], t[:, 1:]
            with torch.autocast(device, dtype=torch.bfloat16, enabled=(device == "cuda")):
                logits = model(x)
            # ★크롭별로 따로 잰다 — paired 비교는 크롭 단위 대응이 있어야 성립한다.
            per = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)).float(),
                y.reshape(-1), reduction="none").reshape(y.shape).mean(dim=1)
            out.extend(float(v) for v in per)
    model.clear_quant()
    model.train()
    model.set_anneal(was)
    return out, n_crop * seq


def paired_stats(a, b):
    """a - b 의 paired 통계. t 는 정규근사로만 읽는다(자유도가 크므로 무방)."""
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    m = sum(d) / n
    sd = statistics.stdev(d) if n > 1 else float("nan")
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = m / se if se else float("nan")
    win = sum(1 for v in d if v < 0)
    return m, sd, se, t, n, win


def main():
    ap = argparse.ArgumentParser(description="P032 결정적 full-val + paired 비교")
    ap.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    ap.add_argument("--dump-crops", default=None, metavar="OUT.json",
                   help="★P078 단계0 — 크롭별 손실을 json 으로 저장한다. "
                        "{tag: [손실...]} 구조이고 `diag_visit_selectivity.py` 가 읽는다. "
                        "평균만 보면 재귀 이득이 **골고루 퍼진 것인지 일부 크롭에 몰린 것인지** "
                        "구분되지 않는다 — 그것이 P078 의 H1(용량설) vs H2(선택설)다")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--micro-bs", type=int, default=8)
    ap.add_argument("--device", default=None)
    # ★★P062(2026-08-15) — **추론 스케줄을 명시할 수 있어야 한다.**
    #   `visit_schedule()` 은 `self.training` 일 때만 `train_repeat` 을 보는데 이 도구는
    #   `model.eval()` 을 부른다 → **`--train-repeat` 로 학습한 체크포인트가 학습과 다른
    #   함수로 평가된다**(계측함정 39, 결과 043 §14 · 047).
    #   ⚠️★**2026-08-22 철회** — 종전 주석은 *"서로 다른 스케줄을 섞는 것은 paired 설계의
    #   전제를 깨므로 일부러 태그별 지정을 안 만들었다"* 였다. **그 판단이 틀렸다.**
    #   paired 는 **크롭 대응**만 요구하지 모델 함수가 같기를 요구하지 않는다. 아래
    #   `--infer-repeat-per-tag`·`--match-train-repeat` 를 참조.
    ap.add_argument("--infer-repeat", type=float, default=1.0,
                    help="(P062) middle 블록 통과 배수. 1.0=종전=비트 동일")
    ap.add_argument("--repeat-where", choices=["front", "back", "even"], default="front",
                    help="(P062) 분수/확장에서 어디를 더 돌지. 학습 uniform 과 같은 것은 front")
    ap.add_argument("--emb-quant", choices=["bf16", "fp16", "int8", "int4", "ternary"],
                    default=None, help="(P034 단계5) 임베딩 양자화. 모든 태그에 걸린다")
    # ★★2026-08-23 실사고 — `--emb-quant X --models A B` 는 X 를 **두 모델 모두**에 건다.
    #   그래서 "양자화의 대가" 가 아니라 "양자화 상태에서 두 체크포인트의 차" 를 잰다.
    #   결과 016 §단계5 에서 bf16 과 int8 이 **정확히 같은 +0.0012** 를 낸 것이 그 증거다.
    ap.add_argument("--emb-quant-per-tag", nargs="*", default=None, metavar="TAG=FMT",
                    help="★(P034 단계5) 태그별. 같은 체크포인트를 두 번 넣으려면 TAG#2 접미사")
    ap.add_argument("--emb-chunk", type=int, default=0,
                    help="(P034 단계5) 헤드 청크 크기. 0=끄기")
    ap.add_argument("--repeat-kv-reuse", action="store_true",
                    help="(P062) 반복 통과에서 첫 통과 KV 재사용(대조 조건)")
    # ★★2026-08-22 사용자 허가 6.5-2 — **태그별 추론 스케줄.**
    #   위 주석(§114~119)이 *"일부러 안 만들었다"* 라고 적어 뒀는데, 그 판단이 틀렸다:
    #   재귀 모델(R=2 로 학습)과 비재귀 기준선(R=1 로 학습)을 **같은 R 로 평가하면
    #   둘 중 하나는 반드시 학습과 다른 함수**로 평가된다 = 함정 39 를 피할 수 없다.
    #   ★**올바른 비교는 "각자 자기가 학습된 함수에서" 다.** paired 설계는 크롭 대응만
    #   요구하고 모델 함수가 같기를 요구하지 않는다.
    ap.add_argument("--infer-repeat-per-tag", nargs="*", default=None, metavar="TAG=R[:WHERE]",
                    help="★(6.5-2) 태그별 추론 배수. 예: mC_r20_nokd=2.0:front mC_initonly=1.0")
    ap.add_argument("--match-train-repeat", action="store_true",
                    help="★★(6.5-2) **각 체크포인트의 `train_repeat`·`repeat_mode` 를 읽어** "
                         "추론 스케줄을 자동으로 맞춘다. 함정 39 를 구조적으로 닫는다")
    ap.add_argument("--reuse-attn-on-dup", action="store_true",
                    help="★(P049 §17.3) 재귀 통과에서 어텐션 출력 재사용. **학습과 같은 값**을 준다")
    a = ap.parse_args()

    # ★임베딩 양자화 per-tag
    emb_map = {}
    for spec in (a.emb_quant_per_tag or []):
        assert "=" in spec, f"형식은 TAG=FMT 다: {spec}"
        k, v = spec.split("=", 1)
        emb_map[k.strip()] = (None if v.strip().lower() in ("none", "off", "-")
                              else v.strip())

    # ── 태그별 스케줄 파싱
    per_tag = {}
    for spec in (a.infer_repeat_per_tag or []):
        assert "=" in spec, f"형식은 TAG=R[:WHERE] 다: {spec}"
        t, v = spec.split("=", 1)
        w = a.repeat_where
        if ":" in v:
            v, w = v.split(":", 1)
        assert w in ("front", "back", "even"), f"where 는 front|back|even: {w}"
        per_tag[t.strip()] = (float(v), w)
    if per_tag and a.match_train_repeat:
        print("  ⚠️ `--infer-repeat-per-tag` 가 `--match-train-repeat` 보다 우선한다(명시가 이긴다)")

    # ★학습 mode -> 추론 where 대응표. **여기가 단일 소스**다(함정 18: 두 곳에서 정하지 않는다)
    MODE2WHERE = {"uniform": "front", "inplace": "even"}

    import torch
    from tinylm import paths
    from tinylm.data import prepare
    META = {}                     # ★2026-08-26 태그 -> 런 json(분해능 자동 선택)
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    base = f"{a.preset}_{a.data}_{a.tokens}"
    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))

    banner("P032 — 결정적 full-val + paired per-crop 비교 (학습 없음)", "#")
    print(f"  device={dev}  seq={a.seq}  micro_bs={a.micro_bs}  data={a.data} {a.tokens}")
    print("  ★val 을 겹치지 않게 전부 순회한다 → eval 샘플링 노이즈 성분 = 0.")
    print("  ★크롭별 손실을 저장해 두 모델을 **같은 크롭 위에서** 뺀다.")
    print("  ⚠️ 이것은 **체크포인트 간** 비교다. 아키텍처 우열은 여기서 나오지 않는다.")

    meta = prepare(a.data, n_tok)
    per = {}
    for tag in a.models:
        # ★`TAG#2` 는 같은 체크포인트를 다른 설정으로 한 번 더 넣는 표기다
        real_tag = tag.split("#", 1)[0]
        ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, real_tag)
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        _eq = emb_map.get(tag, a.emb_quant)
        if tag in emb_map:
            print(f"\n  [emb] {tag}: 임베딩 양자화 = {_eq or '없음'} (per-tag)")
        model, cfg, _ = load_model(arch=_arch_of(real_tag), ckpt_path=str(ck), device=dev,
                                   emb_quant=_eq, emb_chunk=a.emb_chunk)
        # ★2026-08-26 (지시 12) — **분해능 자동 선택용 조건**을 여기서 모은다.
        #   ⚠️`cfg` 가 아니라 **런 json** 이 정본이다 — `kd`·`init_from_src` 는 학습 조건이고
        #   체크포인트 cfg 에는 안 실릴 수 있다.
        try:
            import json as _json
            _jp = ROOT / "runs" / "logs" / f"{ck.stem}.json"
            META[tag] = _json.loads(_jp.read_text(encoding="utf-8")) if _jp.exists() else {}
        except Exception:                                            # noqa: BLE001
            META[tag] = {}
        # ★P062 — 추론 전용 설정만 덮어쓴다(가중치 불변). `cli.py` L308~316 과 같은 규약.
        _tr = float(getattr(cfg, "train_repeat", 1.0) or 1.0)
        _tm = str(getattr(cfg, "repeat_mode", "uniform") or "uniform")
        # ★(6.5-2) 이 태그에 걸 R·where 를 정한다 — 우선순위: per-tag > match-train > 전역
        if tag in per_tag:
            _R, _W, _src = per_tag[tag][0], per_tag[tag][1], "per-tag"
        elif a.match_train_repeat:
            if _tr != 1.0 and _tm not in MODE2WHERE:
                print(f"\n  🚫★{tag}: repeat_mode={_tm} 는 **추론 짝이 없다**"
                      f"(front/back/even 중 어느 것도 아니다). 이 태그는 건너뛴다.")
                del model
                continue
            _R, _W, _src = _tr, MODE2WHERE.get(_tm, "front"), f"train({_tm})"
        else:
            _R, _W, _src = a.infer_repeat, a.repeat_where, "전역"

        # ★★(6.5-1 + 6.5-2) `--match-train-repeat` 는 **`reuse_attn_on_dup` 도 체크포인트에서 읽는다.**
        #   "각자 자기가 학습된 함수로" 를 재귀 배수에만 적용하고 어텐션 재사용에는 안 하면
        #   **같은 함정 39 를 다른 축에서 다시 밟는다.**
        _RA = bool(getattr(cfg, "reuse_attn_on_dup", False)) if a.match_train_repeat \
            else a.reuse_attn_on_dup
        if a.match_train_repeat and _RA != a.reuse_attn_on_dup:
            print(f"  [reuse-attn] {tag}: 체크포인트가 학습된 값 {_RA} 를 쓴다"
                  f"(명령줄 {a.reuse_attn_on_dup} 대신)")
        if _R != 1.0 or a.repeat_kv_reuse or _RA:
            cfg.infer_repeat = _R
            cfg.repeat_where = _W
            cfg.repeat_kv_reuse = a.repeat_kv_reuse
            cfg.reuse_attn_on_dup = _RA
            _sch = model.visit_schedule()
            print(f"\n  [P062] {tag}: infer_repeat={_R} where={_W} [{_src}] "
                  f"kv_reuse={a.repeat_kv_reuse} reuse_attn={_RA} "
                  f"-^> 층 통과 {len(_sch)}회(기준 {cfg.n_layers}회)")
        else:
            cfg.infer_repeat, cfg.repeat_kv_reuse = 1.0, False
            cfg.reuse_attn_on_dup = False
        if abs(_R - _tr) > 1e-9:
            print(f"\n  🚫★{tag}: 학습 train_repeat={_tr}({_tm}) 인데 **추론 R={_R}({_W})** 다 "
                  f"→ **학습과 다른 함수로 평가된다**(계측함정 39). "
                  f"의도한 대조가 아니면 `--match-train-repeat` 를 쓸 것.")
        losses, used = full_val_losses(model, cfg, meta["dir"], a.seq, a.micro_bs, dev)
        per[tag] = losses
        mean = sum(losses) / len(losses)
        print(f"\n  {tag:<16} full-val {mean:.4f}   크롭 {len(losses)}개 / {used:,} 토큰")
        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    if len(per) < 2:
        print("\n  비교할 모델이 2개 미만이다.")
        return 2

    # 크롭 수가 다르면 대응이 깨진다. 같은 data/seq 면 같아야 하므로 방어적으로 자른다.
    n = min(len(v) for v in per.values())
    for k in per:
        per[k] = per[k][:n]

    banner("결정적 full-val (같은 체크포인트면 재실행해도 동일한 값)")
    print(f"  {'모델':<16}{'full-val':>10}{'크롭 표준편차':>14}")
    print("  " + "-" * 44)
    for tag, v in sorted(per.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        print(f"  {tag:<16}{sum(v)/len(v):>10.4f}{statistics.stdev(v):>14.4f}")

    banner("★paired per-crop 비교 — 이것이 판정의 근거다")
    print(f"  {'A vs B':<30}{'mean(A-B)':>12}{'SE':>9}{'t':>8}{'A 승률':>9}  판정")
    print("  " + "-" * 88)
    # ★★★2026-08-26 (사용자 지시 12) — **분해능은 조건 의존이다.** 4세션 미구현이었다.
    #
    #   🚫**무엇이 문제였나**: 이 도구는 조건과 무관하게 **0.024** 를 찍어 왔다.
    #   그런데 0.024 는 **dense·부모 없음** 조건의 2σ 다(결과 012). 현 표준조건은
    #   **무KD + 부모초기화**이고 그 2σ 는 **0.0034**(결과 049) — **7배 예민**하다.
    #   ★실사고: 결과 040·047 이 무KD 비교에 0.024 를 찍어 *"동급"* 이라 적었다.
    #
    #   ★규약: **체크포인트의 조건에서 자를 고른다**(사람이 고르지 않는다).
    #   ⚠️**이것은 통계 검정력이 아니라 실무 의사결정 규칙**이다. `t` 는 따로 인쇄된다.
    #
    # ★★★2026-08-30 갱신 — **자를 세 시드로 다시 쟀고 계열별로 갈렸다**(결과 039 §9·§10).
    #
    #   🚫**0.0034 는 시드 한 쌍으로 얻은 값**이었다. 그런데 **두 점의 차는 σ 가 아니라
    #   σ√2 의 기댓값**에 가깝다 — 그 규약이 **체계적으로 과대평가**했다.
    #   세 시드로 다시 재니 **절반이 됐다**:
    #
    #       타잉  3.6762 / 3.6768 / 3.6765  ->  2σ = 0.0006   (종전 0.0010)
    #       dense 3.6776 / 3.6755 / 3.6762  ->  2σ = 0.0021   (종전 0.0042)
    #       재귀  3.6750 / 3.6747           ->  2σ = 0.0006   ★실측. 더는 빌리지 않는다
    #
    #   ★그래서 결과 059 §13 의 **"R=6 기각" 이 철회**됐다(059 §15) — 20→28 방문
    #   −0.0036 이 빌린 자로는 0.86배였는데 실측 자로는 **6.0배 유의**다.
    #   🚫**이 도구가 0.0034 를 계속 찍으면 같은 종류의 오판이 다시 난다**(5.7배 과대).
    #
    #   ★계열 판정: 재귀(train_repeat>1) · 타잉(mlp_group>1) · dense. **계열이 갈리면
    #   큰 자(dense 0.0021)를 쓴다** — 보수적 선택이고 종전 규칙 2 와 같은 취지다.
    _RULER = {"재귀": (0.0006, "재귀 2σ 실측(결과 039 §10)"),
              "타잉": (0.0006, "타잉 2σ 3시드(결과 039 §9)"),
              "dense": (0.0021, "dense 2σ 3시드(결과 039 §9)")}

    def _family(t):
        m = META.get(t) or {}
        if float(m.get("train_repeat") or 1.0) > 1.0:
            return "재귀"
        return "타잉" if int(m.get("mlp_group") or 1) > 1 else "dense"

    def _sigma_band(tag_a, tag_b):
        def cond(t):
            m = META.get(t) or {}
            return (not bool(m.get("kd", False))) and bool(m.get("init_from_src"))
        if not (cond(tag_a) and cond(tag_b)):
            # KD 가 섞였거나 부모초기화가 없다 — 계열 자를 잰 조건이 아니다.
            return (0.024, "dense·부모없음 2σ(결과 012) — 계열 자 적용 밖")
        fa, fb = _family(tag_a), _family(tag_b)
        if fa == fb:
            return _RULER[fa]
        band, why = max((_RULER[fa], _RULER[fb]), key=lambda x: x[0])
        return (band, f"{why} — 계열 교차({fa}↔{fb})라 큰 자를 쓴다")
    _bands = set()
    for x, y in itertools.combinations(per, 2):
        m, sd, se, t, nn, win = paired_stats(per[x], per[y])
        RES, _why = _sigma_band(x, y)
        _bands.add((RES, _why))
        # |t| ^> 2 면 "이 두 체크포인트는 다르다". 크기 판정은 분해능과 따로 본다.
        if abs(t) < 2:
            verdict = "구분 불가(체크포인트 수준에서도)"
        elif abs(m) < RES:
            verdict = (f"차이 유의하나 분해능({RES}) 미만 — 실무상 동급"
                       + (" ⚠️통계적으로는 유의" if abs(t) > 2 else ""))
        else:
            verdict = "★유의하고 분해능 초과"
        print(f"  {x + ' vs ' + y:<30}{m:>+12.4f}{se:>9.4f}{t:>8.2f}{win/nn:>8.1%}  {verdict}")
    print()
    for _r, _w in sorted(_bands):
        print(f"  ★쓴 자: **{_r}** — {_w}")
    if len(_bands) > 1:
        print("  ⚠️★**쌍마다 자가 다르다.** 조건이 섞여 있다는 뜻이므로 한 표에 나란히 적을 때")
        print("     반드시 **어느 쌍이 어느 자였는지** 함께 적을 것(함정 28).")
    print("  ⚠️분해능은 **실무 의사결정 규칙**이지 통계 검정력이 아니다 — `t` 를 함께 읽는다.")
    print("  ⚠️'실무상 동급' 이라고 적을 때는 **통계적으로는 유의**를 함께 적는다(CLAUDE.md).")

    print("""
  읽는 법
    · SE 가 결과 012 의 σ=0.012 보다 **한 자릿수 작다**면 paired 설계가 의도대로 작동한 것이다.
    · |t| ^> 2 는 "이 두 **체크포인트**가 다르다"만 말한다. 시드가 하나이므로
      **아키텍처 우열의 근거가 아니다.** 그 주장에는 여러 시드가 필요하다(P032 §2.2).
    · 'A 승률' 은 크롭 중 A 가 이긴 비율이다. 평균이 작아도 승률이 한쪽으로 크게 쏠리면
      일관된 차이이고, 50% 근처면 큰 크롭 몇 개가 평균을 끌고 있는 것이다 — 둘은 다르다.

  한계
    · full-val 은 **결정적**이지만 **여전히 이 val 셋**이다. 데이터 문제(P037)는 그대로 남는다.
    · 크롭 경계에서 컨텍스트가 끊긴다(긴 문서에 약간 불리). 두 모델에 공통이라 차이에서는 상쇄된다.
    · bf16 autocast(cuda)면 크롭별 손실에 ULP 노이즈가 섞인다. 정밀 비교는 --device cpu 로
      한 번 더 확인한다(느리지만 fp32).""")

    # ★★P078 단계0 (2026-08-31) — 크롭별 손실을 그대로 남긴다.
    #
    #   왜: 위 표는 **평균과 승률**만 준다. 그런데 P078 의 질문은
    #   *"재귀의 이득이 모든 크롭에 조금씩 퍼져 있는가(H1 용량설), 아니면
    #   일부 크롭에 몰려 있는가(H2 선택설)"* 다. 평균으로는 그 둘이 구분되지 않는다.
    #   ★분포를 보려면 **원자료**가 필요하고, 그것을 여기서 저장한다.
    #   그 다음 분석은 `scripts/diag_visit_selectivity.py` 가 **torch 없이** 한다.
    if a.dump_crops:
        import json as _json
        _out = Path(a.dump_crops)
        _out.parent.mkdir(parents=True, exist_ok=True)
        _payload = {
            "meta": {"preset": a.preset, "data": a.data, "tokens": a.tokens,
                     "seq": a.seq, "micro_bs": a.micro_bs, "device": dev,
                     "match_train_repeat": bool(a.match_train_repeat),
                     "infer_repeat": a.infer_repeat,
                     "n_crops": len(next(iter(per.values()))) if per else 0},
            "crops": {k: [float(x) for x in v] for k, v in per.items()},
        }
        _out.write_bytes((_json.dumps(_payload, ensure_ascii=False)).encode("utf-8"))
        print(f"\n  ★크롭별 손실을 저장했다: {_out}  "
              f"(모델 {len(per)}개 x 크롭 {_payload['meta']['n_crops']}개)")
        print("     분석: python scripts/diag_visit_selectivity.py "
              f"--crops {_out} --base <기준태그> --deep <재귀태그>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
