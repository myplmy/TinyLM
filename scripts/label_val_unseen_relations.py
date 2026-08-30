"""고밀도 val 에 **일반화 슬라이스 라벨**을 붙인다 (2026-08-30 사용자 승인).

★왜 (품질검토 §17)
    고밀도 val 의 `relations` **종류** 중 **30.1%(34/113)** 가 train 에 없다.
    사용자 답변: *"의도한 바는 아니다."* 그러면 `val_loss` 가 두 가지를 섞어 잰다 —
    *"학습한 관계를 얼마나 아는가"* 와 *"안 배운 관계가 나오면 어떻게 되는가"*.
    체크포인트 선택이 그 혼합 위에서 이뤄지고 있었다.

★그런데 실측하니 **조치의 성격이 바뀌었다**
    "30.1%" 는 **관계 종류(type)** 의 비율이다. **레코드 기준으로는 77/600 = 12.8%** 다 —
    안 배운 관계가 **희소 꼬리**에 몰려 있기 때문이다.
    §17.3 이 요구한 일반화 슬라이스 목표가 **10~15%** 였으므로,
    ★**이 val 은 이미 그 설계에 들어 있다. 없던 것은 라벨뿐이다.**
    → 🚫**재생성하지 않는다.** ✅**라벨만 붙인다**(§17.4).

⚠️★**단 평균이 파일 편차를 가린다** — v01 14.7% · **v02 0.0%** · **v03 36.7%** · v04 0.0%.
    **파일 하나로 평가하면 대역 밖**이다. 그래서 라벨이 더 필요하다.

★어휘를 무엇으로 정하나 — **identity train 만** 쓴다
    `(2)attribute` train 은 **다른 AI 가 지금 쓰고 있다**(v18~v20 이 세션 중에 늘었다).
    ✅**실측 확인**: attribute 를 어휘에 더해도 미학습 종류가 **34개로 같다.**
    → **라벨이 그 작업 때문에 흔들리지 않는다.** 그래도 근거를 파일에 박아 둔다.

무엇을 쓰는가 (레코드마다 2필드, **덧붙이기만** 한다)
    "unseen_relation"  : bool  — 이 레코드가 train 에 없는 관계를 하나라도 쓰는가
    "unseen_relations" : list  — 그 관계 이름들(없으면 빈 배열)
그리고 파일 최상단에 `generalization_slice` 블록으로 **언제·무엇을 근거로** 붙였는지 남긴다.

    python scripts/label_val_unseen_relations.py --check    # 안 쓰고 세기만
    python scripts/label_val_unseen_relations.py --apply    # 실제로 쓴다
"""
from __future__ import annotations
import argparse
import collections
import datetime as _dt
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets" / "TinyDataset" / "stage1_highdensity_dataset"
TRAIN_GLOB = "train/stage1_(1)identity_high_density_train_v*.json"
VAL_GLOB = "val/stage1_(1)identity_high_density_val_v*.json"

_NL = chr(10)
_INLINE_MARK = _NL + '    {"'          # 레코드가 한 줄에 하나로 들어간 모양


def records(d):
    return d if isinstance(d, list) else (d.get("records") or d.get("data") or [])


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def style_of(p: Path) -> dict:
    """원본 파일의 **표기 양식**을 읽는다.

    ⚠️★**네 파일의 양식이 서로 다르다**(생성 시점이 달라서다).
        v01·v03 : `"key":"value"` · **레코드 한 줄에 하나** · 끝에 개행 있음
        v02·v04 : `"key": "value"` · **레코드가 여러 줄로 펼쳐짐** · 끝에 개행 없음
    한쪽으로 통일해서 되쓰면 **안 바뀐 줄까지 2,100줄이 diff 에 뜬다.**
    그러면 *"무엇을 더했는지"* 를 사람이 볼 수 없고 검토가 불가능해진다.
    → 감지해서 **원본 양식 그대로** 되쓴다. `emit()` 이 그것을 재현한다.
    """
    t = p.read_text(encoding="utf-8")
    i = t.find('"records"')
    return {"sep": (",", ": ") if '": "' in t[:400] else (",", ":"),
            "inline": _INLINE_MARK in t[i:i + 400],
            "eol_nl": t.endswith(_NL)}


def emit(d, st: dict) -> bytes:
    """`style_of` 가 읽은 양식으로 직렬화한다."""
    sep = st["sep"]
    shell = {k: ("@@RECORDS@@" if k == "records" else v) for k, v in d.items()}
    txt = json.dumps(shell, ensure_ascii=False, indent=2, separators=sep)
    recs = d["records"]
    if st["inline"]:
        rows = ["    " + json.dumps(r, ensure_ascii=False, separators=sep) for r in recs]
        body = "[" + _NL + ("," + _NL).join(rows) + _NL + "  ]"
    else:
        body = json.dumps(recs, ensure_ascii=False, indent=2,
                          separators=sep).replace(_NL, _NL + "  ")
    txt = txt.replace('"@@RECORDS@@"', body)
    return (txt + (_NL if st["eol_nl"] else "")).encode("utf-8")


def dump(p: Path, d, st: dict) -> int:
    """★encode → 임시파일 → os.replace. `write_text` 는 실패 시 0바이트를 남긴다(함정 35)."""
    b = emit(d, st)
    assert len(b) > 1000, f"{p.name}: 직렬화 결과가 너무 작다 ({len(b)}B)"
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    os.close(fd)
    Path(tmp).write_bytes(b)
    os.replace(tmp, p)
    return len(b)


def train_vocab() -> tuple[collections.Counter, list[str]]:
    v: collections.Counter = collections.Counter()
    used: list[str] = []
    for p in sorted(DS.glob(TRAIN_GLOB)):
        used.append(p.name)
        for r in records(load(p)):
            v.update(r.get("relations") or [])
    return v, used


def main() -> int:
    ap = argparse.ArgumentParser(description="고밀도 val 일반화 슬라이스 라벨")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="세기만 한다(쓰지 않는다)")
    g.add_argument("--apply", action="store_true", help="라벨을 파일에 쓴다")
    a = ap.parse_args()

    vocab, used = train_vocab()
    if not vocab:
        print(f"[!] train 파일을 못 찾았다: {DS / TRAIN_GLOB}")
        return 1
    print(f"train 어휘: {len(vocab)}종 (파일 {len(used)}개, identity 만)")

    vals = sorted(DS.glob(VAL_GLOB))
    if not vals:
        print(f"[!] val 파일을 못 찾았다: {DS / VAL_GLOB}")
        return 1

    tot = un = 0
    bad: list[str] = []
    seen_types: collections.Counter = collections.Counter()
    unseen_types: collections.Counter = collections.Counter()
    stamp = _dt.date.today().isoformat()

    for p in vals:
        st = style_of(p)
        # ★★왕복 자기검증 — **고치기 전에** 원본을 그대로 재현할 수 있는지 먼저 본다.
        #   재현이 안 되는 파일은 손대지 않는다. 못 되돌리는 편집을 막는 유일한 장치다.
        if emit(load(p), st) != p.read_bytes():
            print(f"  [E] {p.name}: 양식 왕복 재현 실패 — 이 파일은 건드리지 않는다")
            bad.append(p.name)
            continue
        d = load(p)
        rs = records(d)
        n_un = 0
        for r in rs:
            rel = r.get("relations") or []
            miss = [x for x in rel if x not in vocab]
            for x in rel:
                (unseen_types if x not in vocab else seen_types)[x] += 1
            r["unseen_relation"] = bool(miss)
            r["unseen_relations"] = miss
            n_un += bool(miss)
        tot += len(rs)
        un += n_un
        print(f"  {p.name:52s} {len(rs):4d}건 중 미학습 {n_un:3d}건 "
              f"({n_un / max(len(rs), 1) * 100:4.1f}%)")
        if a.apply:
            if isinstance(d, dict):
                d["generalization_slice"] = {
                    "labeled_on": stamp,
                    "labeled_by": "scripts/label_val_unseen_relations.py",
                    "rationale": ("품질검토 §17.3 — 주 val 은 '학습한 관계를 얼마나 아는가' 를 "
                                  "재고, 일반화 슬라이스는 '안 배운 관계에서 어떻게 되는가' 를 "
                                  "잰다. 섞여 있는 것이 문제였지 존재가 문제가 아니었다."),
                    "vocabulary_source": "train/stage1_(1)identity_high_density_train_v*.json",
                    "vocabulary_files": len(used),
                    "vocabulary_size": len(vocab),
                    "note": ("attribute train 을 어휘에 더해도 미학습 관계 종류가 34개로 "
                             "같았다(2026-08-30 실측). 그 코퍼스가 커져도 이 라벨은 흔들리지 "
                             "않지만, 커지면 --check 로 다시 확인한다."),
                    "unseen_records": n_un,
                    "total_records": len(rs),
                }
            print(f"    -> 기록 {dump(p, d, st)}B  (양식 {st})")

    if bad:
        print(f"{_NL}  [E] 양식 재현 실패로 건너뛴 파일: {bad}")
        return 1

    print(f"{_NL}★합계: 미학습 관계를 쓰는 레코드 {un}/{tot} = {un / tot * 100:.1f}%")
    print(f"  관계 종류: 학습됨 {len(seen_types)}종 / 미학습 {len(unseen_types)}종 "
          f"= 미학습 {len(unseen_types) / (len(seen_types) + len(unseen_types)) * 100:.1f}%")
    print("  ★종류 기준과 레코드 기준이 다르다 — 인용할 때 어느 쪽인지 밝힌다(함정 1 계열).")
    print(f"  미학습 상위: {unseen_types.most_common(10)}")
    band = 10.0 <= un / tot * 100 <= 15.0
    print(f"{_NL}  §17.3 목표대역 10~15% : {'✅안에 있다' if band else '⚠️밖이다'}")
    print("  ⚠️단 파일별로는 0.0%~36.7% 로 갈린다 — **파일 하나로 평가하지 않는다.**")
    if not a.apply:
        print(f"{_NL}  (--check 였으므로 아무것도 쓰지 않았다. 쓰려면 --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
