#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""결과 그림 생성기 — **사용자용 png**. AI 는 결과문서의 텍스트 그래프를 읽는다.

★왜 있나 (2026-08-24 사용자 지시)
    결과문서의 아스키 그래프는 AI 가 읽기에 충분하지만 **사람에게는 불편하다.**
    같은 수를 png 로도 낸다. 🚫**두 그림이 다른 수를 말하면 안 되므로
    출처를 각 그림 캡션에 결과문서 번호로 박는다.**

★규약
    · **라벨은 전부 ASCII** 다. 한글 폰트가 없는 기계에서 네모로 깨지는 것보다 낫다
      (Windows·리눅스 양쪽에서 돌아야 한다). 설명은 결과문서가 한글로 한다.
    · 수치 정본은 `runs/logs/*.json` 과 **결과문서**다. 아래 `TABLE` 은 그 사본이고
      **출처 결과문서 번호를 함께 적는다**. 정본이 바뀌면 여기를 고친다.
    · 학습·GPU 를 쓰지 않는다. `matplotlib` 만 필요하다.

사용법
    python scripts/plot_results.py --all
    python scripts/plot_results.py --fig levers
    python scripts/plot_results.py --fig layermap --layermap-log test_result/057_log_*.txt
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test_result" / "fig"

# ──────────────────────────────────────────────────────────────────────────────
#  수치 표 — ★출처를 결과문서 번호로 박는다. paired full-val 은 json 에 없다.
# ──────────────────────────────────────────────────────────────────────────────
CTRL = 3.6776          # mC_initonly  (결과 038 · B.6)
CTRL_D36 = 3.6848      # mC_d36_ag4_nokd (결과 044 · B.6)
SIGMA2 = 0.0034        # 무KD 2 sigma (결과 049)

# tag: (paired full-val, fp32 상주 MiB, int8 상주 MiB, ms/step, 출처)
TABLE = {
    "mC_initonly":      (3.6776, 451.5, 86.9, 2837.0, "038"),
    "mC_cla1":          (3.6508, 474.0, 89.8, 2640.7, "058"),
    "mC_e192_nokd":     (3.6931, 443.3, None, 2770.7, "051/030"),
    "mC_e128_nokd":     (3.7450, 435.1, 70.6, 2580.5, "030"),
    "mC_sp12_4":        (3.6753, 451.5, 86.9, 2523.1, "045"),
    "mC_sp4_12":        (3.6788, 451.5, 86.9, 2492.3, "045"),
    "mC_sp2_14":        (3.6785, 451.5, 86.9, 2489.0, "045"),
    "mC_d36_ag4_nokd":  (3.6848, 379.7, 77.8, 4718.7, "044"),
    "mC_d36_ag8_nokd":  (3.7073, 334.7, 72.0, 4900.5, "044"),
    "mC_d36_ag16_nokd": (3.7220, 312.2, 69.1, 4917.7, "044"),
    "mC_d36_ag4_e128":  (3.7501, 363.3, None, 4944.0, "030"),
    "mC_r20_nokd":      (3.6573, 451.5, 86.9, 4729.4, "041/047"),
    # ★2026-08-26 추가
    "mC_d36_ag4_g32":   (3.6995, 343.7, None, 5329.0, "029"),
    "mC_d36_ag4_r20_nokd": (3.6691, 379.7, None, 8815.8, "047"),
    "mC_d36_ag4_cla1":  (3.6712, 384.2, None, 5480.6, "058"),
    # ★2026-08-27 추가
    "mC_r30_nokd":      (3.6505, 451.5, 86.9, 6878.8, "047"),
    "mC_initonly_nc":   (3.6762, 451.5, 86.9, 2485.4, "051"),
    "mC_cla1_ag4":      (3.6867, 339.0, 72.4, 2595.9, "058"),
    "mC_d36_ag8_cla1":  (3.6911, None, None, 5030.9, "058"),
}


# ──────────────────────────────────────────────────────────────────────────────
#  ★★2026-08-27 — 자백 A7 조치. **이 표가 정본을 이중화한다**는 문제는
#  주석을 다는 것으로 해결되지 않는다(그렇게 해 두고 "조치" 라고 적었다).
#  이제 **정본과 대조하는 코드**를 둔다. `--verify` 는 matplotlib 을 쓰지 않는다.
#  🚫paired full-val 은 json 에 없으므로 **여기서 검증 불가**다 — 그 한계를 인쇄한다.
# ──────────────────────────────────────────────────────────────────────────────
def verify_table() -> int:
    logs = {}
    for fp in sorted((ROOT / "runs" / "logs").glob("*.json")):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            continue
        tag = d.get("tag") or fp.stem.split("_")[-1]
        logs[tag] = d
        logs[fp.stem] = d

    print("=" * 96)
    print("  plot_results TABLE 대 정본(runs/logs/*.json) 대조  — 자백 A7")
    print("=" * 96)
    bad, nojson, noms, ok = [], [], [], 0
    for tag, (fv, res32, res8, ms, src) in sorted(TABLE.items()):
        d = logs.get(tag) or next((v for k, v in logs.items() if k.endswith(tag)), None)
        if d is None:
            nojson.append(tag)
            continue
        j_ms = d.get("ms_step_median")
        if j_ms and abs(j_ms - ms) > max(1.0, 0.02 * j_ms):
            bad.append(f"{tag:<22} ms/step 표 {ms} vs json ms_step_median {j_ms:.1f}")
        elif not j_ms:
            noms.append(tag)
        # ★★2026-08-28 정정 — **상주는 이미 json 에 있다: `runtime_mb`.**
        #   종전에 나는 *"deploy_mb 가 packed 이니 상주는 재계산해야 한다"* 고 적고
        #   `mem_params` 에서 손으로 다시 계산했다. **절반만 맞았다** — 이름이 오해를 부르는 것은
        #   사실이지만 `packed_mb`·`runtime_mb` 가 **처음부터 따로 실려 있었고**
        #   `deploy_mb` 는 trainer.py 가 명시한 **구 로그 호환 별칭**일 뿐이다.
        #   → **정본을 먼저 쓰고**, 없을 때만(구 런) 재계산으로 물러난다.
        mp = d.get("mem_params") or {}
        j_res = d.get("runtime_mb")
        if res32 and j_res:
            if abs(j_res - res32) > max(0.2, 0.005 * j_res):
                bad.append(f"{tag:<22} 상주 표 {res32} vs json runtime_mb {j_res:.1f}")
        elif mp.get("ternary") and res32:
            calc = (mp["ternary"] * 8
                    + sum(mp.get(k, 0) for k in ("emb", "other", "mode", "lora")) * 4) / 2 ** 20
            if abs(calc - res32) > max(0.2, 0.005 * calc):
                bad.append(f"{tag:<22} 상주 표 {res32} vs 재계산 {calc:.1f} (구 런: runtime_mb 없음)")
        if not bad or not bad[-1].startswith(tag):
            ok += 1
    print(f"  표 {len(TABLE)}행 · 대조 성공 {ok} · json 없음 {len(nojson)} · ms_step_median 없음 {len(noms)} · 불일치 {len(bad)}")
    for t in nojson:
        print(f"    - json 없음: {t}  (구 런이거나 태그 표기가 다르다)")
    for b in bad:
        print(f"    🚫 {b}")
    print()
    if noms:
        print(f"    - ms_step_median 이 None 인 구 런 {len(noms)}개: {', '.join(noms[:6])}"
              f"{' ...' if len(noms) > 6 else ''} (계약 추가 이전 런이다)")
    print("  ⚠️★**paired full-val 은 json 에 없다** — 이 도구로 검증할 수 없다.")
    print("     그 열의 정본은 결과문서이고, 출처 번호를 표의 마지막 열에 박아 둔다.")
    print("  ⚠️★**`deploy_mb` 는 `packed_mb` 의 구 로그 호환 별칭**이다 — 이름이 배포를 말하지만"
          " 값은 **저장**이다. ★**상주는 같은 json 의 `runtime_mb`** 이고 재계산할 필요가 없다(2026-08-28 정정).")
    return 1 if bad else 0

# ★P067 단계1 — common_bpb(SQuAD, 641,795 토큰). 🚫**위 표와 단위가 다르다**(bpb vs nats)
P067_BPB = [("mC_initonly", 1.3075, "V=32,768 · 교사 없음"),
            ("QT0", 1.3440, "Qwen V=151,936 · 교사 없음"),
            ("Q256T", 1.3362, "Qwen 교사"),
            ("Q64T", 1.3999, "Qwen 교사 + E=64")]
BPB_RES = 0.008          # 실무 분해능(0.024 nats 환산, 결과 053)

# 임베딩 양자화 (mC_initonly 위에서) — 결과 016 §20
EMB_QUANT = [
    # (이름, 상주 '기타' MiB, latent해제+int8 총 상주 MiB, paired 품질 대가, 비고)
    ("fp32",    33.0, 86.9,  0.0000, "baseline"),
    ("bf16",    None, None,  None,   "CRASHED (fixed 08-24)"),
    ("int8",     9.1, 63.1, +0.0001, "essentially free"),
    ("int4",     9.5, 63.4,  None,   "LARGER than int8 - no packing"),
    ("ternary",  9.1, 63.1, +0.5109, "destroys quality"),
]


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130,
                         "font.family": "DejaVu Sans", "axes.grid": True,
                         "grid.alpha": 0.25, "axes.spines.top": False,
                         "axes.spines.right": False})
    return plt


def _save(plt, fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  [ok] {path.relative_to(ROOT)}")
    return path


# ──────────────────────────────────────────────────────────────────────────────
def fig_levers(plt):
    """상주 메모리 vs 품질 — REVIEW3 의 본 그림."""
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    groups = {
        "20L attn_group 1 (m100R1c)": ["mC_initonly", "mC_cla1", "mC_e192_nokd",
                                       "mC_e128_nokd", "mC_r20_nokd"],
        "36L (m100R1d)": ["mC_d36_ag4_nokd", "mC_d36_ag8_nokd",
                          "mC_d36_ag16_nokd", "mC_d36_ag4_e128"],
    }
    mk = {"20L attn_group 1 (m100R1c)": "o", "36L (m100R1d)": "s"}
    for gname, tags in groups.items():
        xs = [TABLE[t][1] for t in tags]
        ys = [TABLE[t][0] for t in tags]
        ax.scatter(xs, ys, s=70, marker=mk[gname], label=gname, zorder=3)
        for t, x, y in zip(tags, xs, ys):
            ax.annotate(t.replace("mC_", ""), (x, y), textcoords="offset points",
                        xytext=(6, 5), fontsize=7.5)
    ax.axhline(CTRL, ls="--", lw=1, color="0.45")
    ax.axhspan(CTRL - SIGMA2, CTRL + SIGMA2, color="0.5", alpha=0.13, zorder=0)
    ax.annotate(f"control mC_initonly {CTRL:.4f}  (band = 2 sigma {SIGMA2})",
                (ax.get_xlim()[1], CTRL), fontsize=7.5, color="0.35",
                ha="right", va="bottom")
    ax.set_xlabel("resident memory, fp32 path (MiB)  -  lower is better")
    ax.set_ylabel("paired full-val (nats)  -  lower is better")
    ax.set_title("TinyLM memory levers: resident vs quality (2026-08-24)\n"
                 "source: results 030 / 038 / 044 / 045 / 047 / 058", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    return _save(plt, fig, "levers_resident_vs_quality.png")


def fig_attn(plt):
    """P057 단계3 — 어텐션 타잉 곡선."""
    tags = ["mC_d36_ag4_nokd", "mC_d36_ag8_nokd", "mC_d36_ag16_nokd"]
    g = [4, 8, 16]
    q = [TABLE[t][0] - CTRL_D36 for t in tags]
    r = [TABLE[t][1] for t in tags]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.2))
    a1.plot(g, q, "o-", color="#c1440e")
    a1.axhline(0, color="0.45", ls="--", lw=1)
    a1.axhspan(-SIGMA2, SIGMA2, color="0.5", alpha=0.13)
    for x, y in zip(g, q):
        a1.annotate(f"{y:+.4f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)
    a1.set_xscale("log", base=2); a1.set_xticks(g); a1.set_xticklabels(g)
    a1.set_xlabel("attn_group"); a1.set_ylabel("delta vs ag4 (nats)")
    a1.set_title("quality cost  (band = 2 sigma)", fontsize=9.5)
    a2.plot(g, r, "s-", color="#1f5673")
    for x, y in zip(g, r):
        a2.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)
    a2.set_xscale("log", base=2); a2.set_xticks(g); a2.set_xticklabels(g)
    a2.set_xlabel("attn_group"); a2.set_ylabel("resident fp32 (MiB)")
    a2.set_title("resident memory", fontsize=9.5)
    fig.suptitle("P057 stage 3 - attention tying on the 36-layer model (result 044)",
                 fontsize=10.5)
    return _save(plt, fig, "P057_attn_group_curve.png")


def fig_emb(plt):
    """P046 단계5 + P034 단계5b — 임베딩 두 축."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.2, 4.3))
    E = [256, 192, 128]
    tg = ["mC_initonly", "mC_e192_nokd", "mC_e128_nokd"]
    d = [TABLE[t][0] - CTRL for t in tg]
    a1.plot(E, d, "o-", color="#c1440e", label="measured")
    lin = [0.0, d[1], d[1] * (256 - 128) / (256 - 192)]
    a1.plot(E, lin, "--", color="0.55", label="linear from E=192")
    a1.axhspan(-SIGMA2, SIGMA2, color="0.5", alpha=0.13)
    for x, y in zip(E, d):
        a1.annotate(f"{y:+.4f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=8)
    a1.invert_xaxis()
    a1.set_xticks(E); a1.set_xlabel("emb_rank E")
    a1.set_ylabel("delta vs mC_initonly (nats)")
    a1.set_title("rank axis is CONVEX: measured 2.2x the linear\nP046 stage 5 (result 030)",
                 fontsize=9.5)
    a1.legend(fontsize=8)
    names = [e[0] for e in EMB_QUANT]
    other = [e[1] if e[1] is not None else 0 for e in EMB_QUANT]
    cols = ["0.6" if e[3] is None else ("#1f7a4d" if abs(e[3]) < SIGMA2 else "#a8202a")
            for e in EMB_QUANT]
    b = a2.bar(names, other, color=cols)
    for r_, e in zip(b, EMB_QUANT):
        txt = "crash" if e[1] is None else f"{e[1]:.1f}"
        a2.annotate(txt, (r_.get_x() + r_.get_width() / 2, max(e[1] or 0, 0.6)),
                    ha="center", va="bottom", fontsize=8)
        if e[3] is not None and e[3] != 0:
            a2.annotate(f"quality {e[3]:+.4f}",
                        (r_.get_x() + r_.get_width() / 2, (e[1] or 0) / 2),
                        ha="center", va="center", fontsize=7, color="white",
                        rotation=90)
    a2.set_ylabel("non-ternary resident term (MiB)")
    a2.set_title("embedding quantisation: int8 is free, ternary is not\n"
                 "P034 stage 5b (result 016 s20)", fontsize=9.5)
    return _save(plt, fig, "P046_P034_embedding.png")


def fig_uneven(plt):
    """P061 단계1 — 같은 메모리, 네 형상."""
    tags = ["mC_sp12_4", "mC_initonly", "mC_sp2_14", "mC_sp4_12"]
    lbl = ["12+4", "8+8 (control)", "2+14", "4+12"]
    d = [TABLE[t][0] - CTRL for t in tags]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = ["#1f7a4d" if abs(v) < SIGMA2 else "#a8202a" for v in d]
    b = ax.bar(lbl, d, color=cols, width=0.55)
    ax.axhspan(-SIGMA2, SIGMA2, color="0.5", alpha=0.16,
               label=f"2 sigma = {SIGMA2} (indistinguishable)")
    ax.axhline(0, color="0.4", lw=1)
    for r_, v in zip(b, d):
        ax.annotate(f"{v:+.4f}", (r_.get_x() + r_.get_width() / 2, v),
                    ha="center", va="bottom" if v >= 0 else "top",
                    fontsize=9, xytext=(0, 3 if v >= 0 else -3),
                    textcoords="offset points")
    ax.set_ylabel("delta vs mC_initonly (nats)")
    ax.set_title("P061 stage 1 - uneven tying, IDENTICAL memory in all four\n"
                 "deploy_mb 13.0503 and resident 451.4875 to the decimal (result 045)",
                 fontsize=10)
    ax.legend(fontsize=8)
    return _save(plt, fig, "P061_uneven_tying.png")


# ──────────────────────────────────────────────────────────────────────────────
GLYPH = " .:-=+*#%@"


def _parse_layermap(path):
    """P072 로그에서 글리프 히트맵과 U2·U3 표를 되읽는다.

    ⚠️★**글리프는 10단계 양자화다.** 그림에는 충분하지만 **수로 쓰면 안 된다.**
    정확한 행렬이 필요하면 `diag_layer_map.py --dump-json` 을 쓴다(2026-08-24 추가).
    """
    txt = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"^  \[(?=[A-Za-z])", txt, flags=re.M)[1:]
    out = []
    for b in blocks:
        name = b.split("]")[0]
        mats = {}
        for key, pat in (("U1", r"\u2500\u2500 U1 [^\n]*\n(.*?)(?=\n\s*\ube44\ub300\uac01|\Z)"),
                         ("U4", r"\u2500\u2500 U4 [^\n]*\n(.*?)(?=\n\s*\ube44\ub300\uac01|\Z)")):
            m = re.search(pat, b, re.S)
            if not m:
                continue
            seg = m.group(1)
            rng = re.search(r"([-+]\d\.\d+)\s*~\s*([-+]\d\.\d+)", seg)
            if not rng:
                continue
            lo, hi = float(rng.group(1)), float(rng.group(2))
            rows = []
            for line in seg.splitlines():
                mm = re.match(r"^\s{6,}(\d+)([ .:\-=+*#%@]+)\s*$", line.rstrip("\r"))
                if mm:
                    rows.append([GLYPH.index(c) for c in mm.group(2) if c in GLYPH])
            if rows:
                w = max(len(r) for r in rows)
                rows = [r + [0] * (w - len(r)) for r in rows]
                mats[key] = ([[lo + (hi - lo) * (v + 0.5) / len(GLYPH) for v in r]
                              for r in rows], lo, hi)
        abl = [(int(x), float(y)) for x, y in
               re.findall(r"^\s+\d+\s+(\d+)\s+([-+]\d+\.\d+)\s", b, re.M)]
        u3 = [(int(a_), float(c)) for a_, _b, c in
              re.findall(r"^\s+(\d+)\s+(\d+)\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s*$", b, re.M)]
        if mats:
            out.append({"name": name, "mats": mats, "abl": abl, "u3": u3})
    return out


def fig_p067(plt):
    """P067 단계1 — 좋은 교사가 KD 를 살렸는가."""
    fig, ax = plt.subplots(figsize=(7.8, 4.3))
    names = [n for n, _v, _w in P067_BPB]
    vals = [v for _n, v, _w in P067_BPB]
    base = dict((n, v) for n, v, _w in P067_BPB)["QT0"]
    cols = ["0.55"] + ["#1f5673", "#1f7a4d", "#a8202a"]
    b = ax.bar(names, vals, color=cols, width=0.55)
    ax.set_ylim(1.28, 1.42)
    for r_, (n, v, w) in zip(b, P067_BPB):
        ax.annotate(f"{v:.4f}", (r_.get_x() + r_.get_width()/2, v),
                    ha="center", va="bottom", fontsize=9,
                    xytext=(0, 3), textcoords="offset points")
        ax.annotate(w, (r_.get_x() + r_.get_width()/2, 1.285),
                    ha="center", va="bottom", fontsize=7, color="0.3", rotation=90)
    ax.axhline(base, ls="--", lw=1, color="#1f5673")
    ax.axhspan(base - BPB_RES, base + BPB_RES, color="#1f5673", alpha=0.10)
    ax.annotate(f"QT0 band = practical resolution {BPB_RES} bpb",
                (len(names) - 0.4, base + BPB_RES), fontsize=7.5, color="#1f5673",
                ha="right", va="bottom")
    ax.set_ylabel("common bpb (SQuAD context) - lower is better")
    ax.set_title("P067 stage 1 - a teacher better than its student wins by 0.0078 bpb,\n"
                 "which is JUST under the 0.008 practical resolution (result 053)",
                 fontsize=10)
    return _save(plt, fig, "P067_teacher_quality.png")


def fig_decomp(plt):
    """P074 의 좌표평면 — 네 요소를 한 그림에(dense 팔은 아직 없다)."""
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    groups = {
        "B  tying (20L)": ["mC_initonly", "mC_cla1"],
        "B  tying (36L)": ["mC_d36_ag4_nokd", "mC_d36_ag8_nokd", "mC_d36_ag16_nokd",
                           "mC_d36_ag4_g32", "mC_d36_ag4_cla1"],
        "D  recursion": ["mC_r20_nokd", "mC_d36_ag4_r20_nokd"],
    }
    mk = {"B  tying (20L)": "o", "B  tying (36L)": "s", "D  recursion": "^"}
    for g, tags in groups.items():
        xs = [TABLE[t][1] for t in tags]; ys = [TABLE[t][0] for t in tags]
        ax.scatter(xs, ys, s=80, marker=mk[g], label=g, zorder=3)
        for t, x, y in zip(tags, xs, ys):
            ax.annotate(t.replace("mC_", ""), (x, y), textcoords="offset points",
                        xytext=(6, 4), fontsize=7)
    for x, lab in ((317, "d6"), (411, "d8"), (505, "d10"), (600, "d12")):
        ax.axvline(x, color="#a8202a", ls=":", lw=1, alpha=0.6)
        ax.annotate(f"A {lab}?", (x, ax.get_ylim()[1]), fontsize=7.5, color="#a8202a",
                    rotation=90, va="top", ha="right")
    ax.axhline(CTRL, ls="--", lw=1, color="0.45")
    ax.axhspan(CTRL - SIGMA2, CTRL + SIGMA2, color="0.5", alpha=0.13, zorder=0)
    ax.set_xlabel("resident memory, fp32 path (MiB)  -  lower is better")
    ax.set_ylabel("paired full-val (nats)  -  lower is better")
    ax.set_title("P074 decomposition frame - A (shallow dense) is the MISSING axis\n"
                 "dotted lines are where the four dense arms will land (estimated)",
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower left")
    return _save(plt, fig, "P074_decomposition_frame.png")


def fig_layermap(plt, logpath):
    models = _parse_layermap(logpath)
    if not models:
        print("  [!] 층 지도 로그에서 행렬을 못 찾았다:", logpath)
        return None
    saved = []
    for m in models:
        keys = [k for k in ("U4", "U1") if k in m["mats"]]
        ncol = len(keys) + (1 if m["abl"] else 0)
        fig, axes = plt.subplots(1, ncol, figsize=(4.6 * ncol, 4.5))
        axes = [axes] if ncol == 1 else list(axes)
        for ax, k in zip(axes, keys):
            mat, lo, hi = m["mats"][k]
            im = ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_title({"U4": "U4  cos(input_i, input_j)",
                          "U1": "U1  cos(delta_i, delta_j)"}[k], fontsize=9.5)
            ax.set_xlabel("visit index"); ax.set_ylabel("visit index")
            ax.grid(False)
            fig.colorbar(im, ax=ax, fraction=0.046, shrink=0.85)
        if m["abl"]:
            ax = axes[-1]
            ls = [l for l, _ in m["abl"]][:24]
            ds = [d for _, d in m["abl"]][:24]
            ax.barh([str(l) for l in ls][::-1], ds[::-1], color="#1f5673")
            ax.set_xscale("symlog", linthresh=0.01)
            ax.set_xlabel("loss increase when layer gate = 0")
            ax.set_ylabel("layer"); ax.set_title("U2  per-layer contribution", fontsize=9.5)
            ax.grid(True, axis="x", alpha=0.25)
        fig.suptitle(f"P072 layer map - {m['name']}   (result 057)\n"
                     "heatmaps reconstructed from the 10-level glyph map: "
                     "picture is faithful, numbers are +-0.05",
                     fontsize=10)
        saved.append(_save(plt, fig, f"P072_layermap_{m['name']}.png"))
    return saved


# ──────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="결과 그림 생성기(사용자용 png)")
    ap.add_argument("--fig", choices=["levers", "attn", "emb", "uneven", "layermap",
                                  "p067", "decomp"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--layermap-log", default=None,
                    help="P072 로그 경로(미지정이면 test_result 에서 최신을 찾는다)")
    ap.add_argument("--verify", action="store_true",
                    help="★TABLE 을 runs/logs/*.json 과 대조만 한다(matplotlib 불필요)")
    a = ap.parse_args()
    if a.verify:
        return verify_table()
    if not a.fig and not a.all:
        ap.error("--fig 또는 --all 중 하나가 필요하다")
    try:
        plt = _plt()
    except ImportError:
        print("[STOP] matplotlib 이 없다. `pip install matplotlib` 후 다시 실행.")
        return 2

    want = ["levers", "attn", "emb", "uneven", "p067", "decomp", "layermap"] if a.all else [a.fig]
    print("=" * 96)
    print("  결과 그림 생성 — ★라벨은 ASCII 다(한글 폰트가 없는 기계에서 깨지지 않게)")
    print("  ⚠️수치 정본은 runs/logs/*.json 과 결과문서다. 이 표는 사본이고 출처를 캡션에 적었다.")
    print("=" * 96)
    for w in want:
        if w == "levers":  fig_levers(plt)
        elif w == "attn":  fig_attn(plt)
        elif w == "emb":   fig_emb(plt)
        elif w == "uneven": fig_uneven(plt)
        elif w == "p067":  fig_p067(plt)
        elif w == "decomp": fig_decomp(plt)
        elif w == "layermap":
            lp = a.layermap_log
            if not lp:
                cand = sorted(glob.glob(str(ROOT / "test_result" / "*P072_stage0*layer_map*.txt")))
                lp = cand[-1] if cand else None
            if not lp:
                print("  [!] P072 로그를 못 찾았다 — --layermap-log 로 지정하세요")
                continue
            fig_layermap(plt, lp)
    print("=" * 96)
    print(f"  저장 위치: {OUT.relative_to(ROOT)}")
    print("  ⚠️그림은 결과문서의 텍스트 그래프와 **같은 수**여야 한다. 다르면 표를 고칠 것.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
