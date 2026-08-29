#!/usr/bin/env python3
"""★학습용 JSON 데이터셋의 **정량 품질 진단**. torch·GPU 0, 외부 의존 0.

## 왜 이 도구가 생겼나 (2026-08-29 사용자 지시)

`datasets/TinyDataset/stage1_highdensity_dataset` 처럼 **여러 파일로 나눠 증축되는 코퍼스**는
사람 눈으로 다음을 못 본다.

  · train ↔ val **오염**(같은 문장이 양쪽에)
  · **완전 중복** 레코드(같은 파일 안 / 파일 사이)
  · ★**근접 중복** — 문장 몇 개만 바꾼 사실상 같은 레코드
  · **문장 단위 반복** — 레코드는 달라도 같은 문장이 수십 번
  · **분량**이 목표치에 맞는가

🚫**이 도구는 "좋은 데이터인가" 를 판정하지 않는다.** 그건 사람이 본다.
✅**세는 것만 한다** — 중복·오염·분포. **세는 것과 판단하는 것을 섞지 않는다.**

## 근접 중복을 어떻게 재나

**문자 8-gram MinHash(64 순열) + 밴딩 LSH(16밴드 × 4)** 로 후보 쌍을 뽑고,
후보에만 **정확한 Jaccard** 를 계산한다. 전수 O(n²) 를 피하면서 재현율을 유지한다.
⚠️**MinHash 는 근사다** — 임계 근처에서 놓치는 쌍이 있다. **하한으로 읽는다.**

사용:
    python scripts/diag_dataset_quality.py --train "datasets/.../train/stage1_identity*.json" \\
                                           --val   "datasets/.../val/stage1_identity*.json"
    python scripts/diag_dataset_quality.py --train ... --val ... --near 0.7 --md out.md
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ★우리 32k 토크나이저의 실측 압축률(결과 053 §S1.7.4) — 토큰 추정은 **이 수 하나에 의존**한다.
BYTES_PER_TOKEN = 4.366
SENT = re.compile(r"[^.!?。\n]+[.!?。]?")
WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return WS.sub(" ", s or "").strip()


def load(patterns):
    """(파일명, 레코드) 목록. `records` 키가 있으면 그 안을, 없으면 최상위 리스트를 쓴다."""
    out = []
    for pat in patterns:
        for fp in sorted(glob.glob(pat)):
            p = Path(fp)
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:                            # noqa: BLE001
                print(f"  ⚠️ 읽기 실패 {p.name}: {type(e).__name__}: {e}")
                continue
            recs = d.get("records") if isinstance(d, dict) else d
            if not isinstance(recs, list):
                print(f"  ⚠️ 레코드 배열을 못 찾았다: {p.name}")
                continue
            for r in recs:
                out.append((p.name, r))
    return out


def shingles(s: str, k: int = 8):
    s = norm(s)
    return {s[i:i + k] for i in range(max(len(s) - k + 1, 1))}


def minhash(sh, n=64):
    if not sh:
        return tuple([0] * n)
    base = [zlib.crc32(x.encode("utf-8")) & 0xFFFFFFFF for x in sh]
    return tuple(min((h ^ (seed * 0x9E3779B1)) & 0xFFFFFFFF for h in base) for seed in range(n))


def near_dup_pairs(texts, thr, bands=16):
    """(i, j, jaccard) — MinHash LSH 후보에만 정확 Jaccard."""
    sigs = [minhash(shingles(t)) for t in texts]
    rows = len(sigs[0]) // bands if sigs else 0
    buckets = defaultdict(list)
    for i, sig in enumerate(sigs):
        for b in range(bands):
            buckets[(b, sig[b * rows:(b + 1) * rows])].append(i)
    cand = set()
    for v in buckets.values():
        if 1 < len(v) <= 200:                       # 거대 버킷은 정보가 없다(전부 같은 틀)
            for a in range(len(v)):
                for c in range(a + 1, len(v)):
                    cand.add((v[a], v[c]))
    sh = {}
    out = []
    for i, j in cand:
        for k in (i, j):
            if k not in sh:
                sh[k] = shingles(texts[k])
        inter = len(sh[i] & sh[j])
        uni = len(sh[i] | sh[j]) or 1
        jac = inter / uni
        if jac >= thr:
            out.append((i, j, jac))
    return sorted(out, key=lambda x: -x[2]), len(cand)


def field_texts(r):
    return norm(r.get("text") or r.get("content") or "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="+", required=True, help="glob 패턴(여러 개 가능)")
    ap.add_argument("--val", nargs="*", default=[], help="glob 패턴")
    ap.add_argument("--near", type=float, default=0.70, help="근접중복 Jaccard 임계(기본 0.70)")
    ap.add_argument("--top", type=int, default=15, help="예시로 인쇄할 개수")
    ap.add_argument("--md", default=None, help="마크다운 표를 이 파일로도 쓴다")
    a = ap.parse_args()

    L = []
    def P(s=""):
        print(s)
        L.append(s)

    tr = load(a.train)
    va = load(a.val) if a.val else []
    P("=" * 96)
    P("  데이터셋 정량 품질 진단 — **세는 것만 한다. 판단은 사람이 한다**")
    P("=" * 96)
    if not tr:
        print("  🚫 train 레코드가 0건이다"); return 1

    tr_txt = [field_texts(r) for _, r in tr]
    va_txt = [field_texts(r) for _, r in va]

    # ── 1. 분량 ────────────────────────────────────────────────────────────────
    def vol(txts):
        b = sum(len(t.encode("utf-8")) for t in txts)
        c = sum(len(t) for t in txts)
        return len(txts), c, b, b / BYTES_PER_TOKEN
    n_t, c_t, b_t, tok_t = vol(tr_txt)
    P("\n## 1. 분량")
    P(f"  {'구분':6} {'레코드':>7} {'문자':>10} {'UTF-8 바이트':>13} {'⚙추정 토큰':>12} {'파일':>5}")
    P(f"  {'train':6} {n_t:>7,} {c_t:>10,} {b_t:>13,} {tok_t:>12,.0f} "
      f"{len({f for f, _ in tr}):>5}")
    if va:
        n_v, c_v, b_v, tok_v = vol(va_txt)
        P(f"  {'val':6} {n_v:>7,} {c_v:>10,} {b_v:>13,} {tok_v:>12,.0f} "
          f"{len({f for f, _ in va}):>5}")
        P(f"  ★val 비중 = {n_v/(n_t+n_v)*100:.1f}% (레코드) · "
          f"{tok_v/(tok_t+tok_v)*100:.1f}% (토큰)")
    P(f"  ⚙토큰 추정 = UTF-8 바이트 / {BYTES_PER_TOKEN} (우리 32k 토크나이저 실측, 결과 053 §S1.7.4)")
    P("  🚫**추정이다** — 정확한 값은 토크나이저를 실제로 돌려야 한다")

    # ── 2. 완전 중복 ───────────────────────────────────────────────────────────
    P("\n## 2. 완전 중복 (정규화 후 문자열 동일)")
    def dup_report(name, items, txts):
        cnt = Counter(txts)
        dups = {k: v for k, v in cnt.items() if v > 1 and k}
        extra = sum(v - 1 for v in dups.values())
        P(f"  {name}: 고유 {len(cnt):,} / 전체 {len(txts):,} · "
          f"중복 그룹 {len(dups):,}개 · **잉여 레코드 {extra:,}건**"
          f" ({extra/max(len(txts),1)*100:.2f}%)")
        for k, v in sorted(dups.items(), key=lambda x: -x[1])[:5]:
            where = sorted({items[i][0] for i, t in enumerate(txts) if t == k})
            P(f"      ×{v}  {k[:66]}…   [{', '.join(w[-14:] for w in where[:4])}]")
        return extra
    e_tr = dup_report("train", tr, tr_txt)
    e_va = dup_report("val", va, va_txt) if va else 0

    ids = Counter(r.get("id") for _, r in tr if r.get("id"))
    dup_id = {k: v for k, v in ids.items() if v > 1}
    P(f"  train `id` 중복: **{len(dup_id)}개** " +
      (f"(예: {', '.join(list(dup_id)[:6])})" if dup_id else "— 없다 ✅"))
    if va:
        vids = Counter(r.get("id") for _, r in va if r.get("id"))
        dv = {k: v for k, v in vids.items() if v > 1}
        P(f"  val `id` 중복: **{len(dv)}개** " + ("" if dv else "— 없다 ✅"))
        cross = set(ids) & set(vids)
        P(f"  ★train ↔ val `id` 충돌: **{len(cross)}개** " +
          (f"(예: {', '.join(sorted(cross)[:6])})" if cross else "— 없다 ✅"))

    # ── 3. 오염 ────────────────────────────────────────────────────────────────
    if va:
        P("\n## 3. ★train ↔ val 오염")
        st, sv = set(tr_txt), set(va_txt)
        both = st & sv
        P(f"  완전 동일 텍스트: **{len(both)}건** ({len(both)/max(len(sv),1)*100:.2f}% of val)"
          + ("" if both else " — 없다 ✅"))
        for t in list(both)[:a.top]:
            P(f"      · {t[:80]}…")

    # ── 4. 근접 중복 ───────────────────────────────────────────────────────────
    P(f"\n## 4. ★근접 중복 (문자 8-gram Jaccard ≥ {a.near})")
    pairs, ncand = near_dup_pairs(tr_txt, a.near)
    P(f"  train 내부: 후보쌍 {ncand:,} → **임계 초과 {len(pairs):,}쌍**")
    for i, j, s in pairs[:a.top]:
        P(f"      {s:.3f}  [{tr[i][0][-18:]}] {tr_txt[i][:52]}…")
        P(f"             [{tr[j][0][-18:]}] {tr_txt[j][:52]}…")
    if va:
        allt = tr_txt + va_txt
        p2, _ = near_dup_pairs(allt, a.near)
        cross = [(i, j, s) for i, j, s in p2
                 if (i < len(tr_txt)) != (j < len(tr_txt))]
        P(f"  ★train ↔ val: **{len(cross)}쌍** 이 임계를 넘는다"
          + ("" if cross else " — 없다 ✅"))
        for i, j, s in cross[:a.top]:
            ti, tj = (i, j) if i < len(tr_txt) else (j, i)
            P(f"      {s:.3f}  train: {allt[ti][:56]}…")
            P(f"             val  : {allt[tj][:56]}…")

    # ── 5. 문장 단위 반복 ──────────────────────────────────────────────────────
    P("\n## 5. 문장 단위 반복 (레코드가 달라도 같은 문장인가)")
    def sents(txts):
        out = []
        for t in txts:
            out += [norm(s) for s in SENT.findall(t) if len(norm(s)) >= 12]
        return out
    s_tr = sents(tr_txt)
    cs = Counter(s_tr)
    rep = {k: v for k, v in cs.items() if v > 1}
    P(f"  train 문장 {len(s_tr):,}개 · 고유 {len(cs):,} · "
      f"**2회 이상 등장 {len(rep):,}종 / 잉여 {sum(v-1 for v in rep.values()):,}개** "
      f"({sum(v-1 for v in rep.values())/max(len(s_tr),1)*100:.2f}%)")
    for k, v in sorted(rep.items(), key=lambda x: -x[1])[:a.top]:
        P(f"      ×{v:>3}  {k[:78]}")
    if va:
        s_va = sents(va_txt)
        cross_s = set(s_va) & set(s_tr)
        P(f"  ★val 문장 {len(s_va):,}개 중 **train 에도 있는 문장 {len(cross_s):,}종**"
          f" ({len(cross_s)/max(len(set(s_va)),1)*100:.2f}% of val 고유문장)")
        for s in list(cross_s)[:a.top]:
            P(f"      · {s[:78]}")

    # ── 6. 분포 ────────────────────────────────────────────────────────────────
    P("\n## 6. 분포")
    lens = [len(t) for t in tr_txt]
    P(f"  train 길이(문자): 최소 {min(lens)} · 중위 {statistics.median(lens):.0f} · "
      f"평균 {statistics.fmean(lens):.0f} · 최대 {max(lens)}")
    for key in ("type", "source_seed"):
        c = Counter(str(r.get(key)) for _, r in tr if key in r)
        if c:
            P(f"  train `{key}`: " + " · ".join(f"{k} {v:,}" for k, v in c.most_common(8)))
    rel = Counter()
    for _, r in tr:
        for x in (r.get("relations") or []):
            rel[x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)[:40]] += 1
    if rel:
        P(f"  train `relations` 어휘 {len(rel)}종 · 상위: " +
          " · ".join(f"{k} {v}" for k, v in rel.most_common(8)))
        singles = sum(1 for v in rel.values() if v == 1)
        P(f"      ⚠️1회만 등장하는 관계 **{singles}종** ({singles/len(rel)*100:.1f}%)")
    con = Counter()
    for _, r in tr:
        for x in (r.get("concepts") or []):
            con[x if isinstance(x, str) else str(x)[:40]] += 1
    if con:
        P(f"  train `concepts` {len(con)}종 · 상위: " +
          " · ".join(f"{k} {v}" for k, v in con.most_common(6)))
    if va:
        cv = Counter()
        for _, r in va:
            for x in (r.get("concepts") or []):
                cv[x if isinstance(x, str) else str(x)[:40]] += 1
        if cv and con:
            ov = set(cv) & set(con)
            P(f"  ★val `concepts` {len(cv)}종 중 **train 과 겹치는 것 {len(ov)}종** "
              f"({len(ov)/len(cv)*100:.1f}%)")

    P("\n" + "=" * 96)
    P(f"  요약: train 잉여 {e_tr}건 · val 잉여 {e_va}건 · 근접중복 {len(pairs)}쌍")
    P("  🚫**이 도구는 세기만 한다.** 어떤 중복이 해로운지는 학습 목적이 정한다.")
    if a.md:
        Path(a.md).write_bytes(("\n".join(L) + "\n").encode("utf-8"))
        print(f"\n  → {a.md} 에 기록")
    return 0


if __name__ == "__main__":
    sys.exit(main())
