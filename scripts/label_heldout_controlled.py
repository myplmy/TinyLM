#!/usr/bin/env python3
"""★held-out 벤치마크의 관계 이름을 **13개 통제 어휘**로 접어 필드를 추가한다.

## 무엇을 왜

`(2)attribute`·`(3)function` 코퍼스는 관계 이름을 **13개만** 쓴다. held-out 벤치마크는
`*_canonical` 로 84종을 쓴다. 슬라이스 평가를 관계별로 하려면 **같은 어휘**여야 한다.

★**추가만 한다**: `required_relations_controlled` · `candidate_relations_controlled`.
🚫**원본 `*_canonical` 은 손대지 않는다** — 채점기가 읽는 필드가 아니므로 **점수 불변**이고,
원본이 남아 있어 **되돌릴 수 있다**(v2.4 분리 불필요 판단의 근거, 핸드오프 2026-08-31 §3.2).

## 🚫`forbidden_relations_canonical` 은 접지 않는다

`wrong_category` · `function_as_identity` 같은 값은 **관계가 아니라 위반 유형**이다.
13개 관계 어휘로 재면 안 되고, 재서도 안 된다(함정 28: 한 이름이 두 양을 가리킨다).
⚠️`candidate_*` 에도 같은 위반 유형이 섞여 있어서, 그것들은 **`other`** 로 간다 —
🚫**`boundary` 같은 진짜 관계에 얹지 않는다.**

## 판정 규약 (이 파일이 유일한 정본)

  · 이름이 아니라 **뜻**으로 접는다. `X_boundary` 라고 자동으로 boundary 가 아니다.
  · 확신이 없으면 **`other`**. 억지로 얹는 것보다 낫다 —
    `other` 는 attribute 코퍼스에서도 921회 쓰이는 정식 항목이다.
  · `A_as_B` 형태(오답 유형)는 **전부 `other`**. 그것은 관계가 아니라 오류 유형이다.
  · `A_vs_B` 형태는 **`boundary`** — *"둘은 같은 종류가 아니다"* 를 말한다.
  · 13개 밖의 새 이름을 만들지 않는다.

사용:
    python scripts/label_heldout_controlled.py --dry-run     # 통계만
    python scripts/label_heldout_controlled.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = (ROOT / "datasets" / "TinyDataset" / "stage1_dataset" / "held-out_v2.3"
         / "stage1_heldout_benchmark_v2.3_300.json")
MAPOUT = ROOT / "docs" / "relation_mapping_heldout_v1.json"

CTRL = {"attribute", "boundary", "comparison", "process", "other", "is_a", "state",
        "contrast", "function", "classification", "part_of", "role", "subclass_of"}

# ── 매핑표 — **뜻으로 접는다.** 근거를 옆에 적는다. ───────────────────────────
MAP: dict[str, str] = {
    # 그대로 있는 것
    "attribute": "attribute", "boundary": "boundary", "comparison": "comparison",
    "function": "function", "is_a": "is_a", "part_of": "part_of", "state": "state",
    # 뜻이 분명한 것
    "not_is_a": "boundary",              # "X 는 Y 가 아니다" = 선긋기
    "concept_type": "classification",    # 개념의 종류를 말한다
    "part": "part_of",
    "containment": "part_of",
    "inside": "part_of",                 # 공간 포함도 부분-전체 칸에 얹는다
    "touching": "boundary",              # 닿음/안닿음은 경계 문제다
    "near": "boundary",
    "near_not_touching": "boundary",
    "intersecting": "boundary",
    "spatial": "other",                  # 13개에 공간 칸이 없다
    "direction": "other",
    "left_right": "other",
    "temporal": "other",                 # 시간 칸도 없다
    "temporal_order": "process",         # 순서는 진행이다
    "simultaneity": "other",
    "causal": "process",                 # 원인-결과는 진행의 한 형태
    "representation": "other",           # 표상 칸이 없다. 억지로 얹지 않는다
    "uncertainty": "other",
    "polysemy": "other",
    "contextual_meaning": "other",
    "equal_comparison": "comparison",
    "inverse_comparison": "comparison",
    "comparison_unknown": "comparison",
    # A_vs_B = 선긋기
    "attribute_vs_category": "boundary", "inside_vs_part_of": "boundary",
    "state_vs_identity": "boundary", "representation_vs_object": "boundary",
    "medium_vs_category": "boundary", "name_vs_identity": "boundary",
    "content_vs_identity": "boundary", "correlation_vs_causation": "boundary",
    "typical_vs_necessary": "boundary", "necessary_vs_sufficient": "boundary",
    "sufficient_vs_necessary": "boundary", "function_vs_identity": "boundary",
    "state_vs_category": "boundary", "habitat_vs_category": "boundary",
    "material_vs_category": "boundary", "unknown_vs_false": "boundary",
    "possible_vs_actual": "boundary", "typical_vs_universal": "boundary",
    "form_vs_meaning": "boundary", "distance_vs_connectivity": "boundary",
    "part_vs_whole_attribute": "boundary", "whole_vs_part_attribute": "boundary",
    "whole_failure_vs_part": "boundary",
    # 복합 서술
    "attached_and_part_of": "part_of",
    "on_not_part_of": "boundary",
    "part_removal_effect": "process",
    "state_projection": "state",
    "causal_uncertainty": "other",
    "different_function": "contrast",     # 같은 축(기능) 위의 다름
    "different_identity": "contrast",
}
# ★A_as_B 형태는 전부 `other` — 관계가 아니라 **오답 유형**이다.
#   이 목록을 하드코딩하지 않고 접미 규칙으로 잡는다(새 이름이 늘어도 안전하다).
AS_SUFFIX_TO_OTHER = True
# ★inverse_* 는 방향 반전이다. 13개에 방향이 없으므로 원형으로 접는다.
INVERSE_PREFIX = "inverse_"

WHY = {
    "other": "13개 어휘에 대응 칸이 없다. 억지로 얹지 않는다",
    "boundary": "A_vs_B 형태 = 둘은 같은 종류가 아니다",
}


def fold(name: str) -> tuple[str, str]:
    """(통제어휘, 사유). 모르면 other."""
    if name in MAP:
        return MAP[name], "표"
    if name.startswith(INVERSE_PREFIX):
        base = name[len(INVERSE_PREFIX):]
        if base in MAP:
            return MAP[base], "inverse_ 접두 제거 후 표(13개에 방향이 없다)"
    if AS_SUFFIX_TO_OTHER and ("_as_" in name or name.endswith("_as_identity")):
        return "other", "A_as_B = 관계가 아니라 오답 유형"
    if name.endswith("_vs_" + name.split("_vs_")[-1]) and "_vs_" in name:
        return "boundary", WHY["boundary"]
    return "other", "매핑표에 없다 - 사람이 볼 것"


def main() -> int:
    ap = argparse.ArgumentParser(description="held-out 관계를 13개 통제 어휘로 접는다")
    ap.add_argument("--write", action="store_true", help="실제로 파일을 고친다")
    ap.add_argument("--bench", default=str(BENCH))
    a = ap.parse_args()

    p = Path(a.bench)
    raw = p.read_bytes()
    d = json.loads(raw.decode("utf-8"))
    recs = d["records"]

    # ★★쓰기 전에 **바이트 왕복 자기시험** — 직렬화가 원본을 바꾸는지 먼저 본다.
    #   (함정 42: 문서를 프로그램으로 고쳤다가 본문이 남의 것이 됐다)
    #   ⚠️★원본이 **CRLF** 다. 그대로 쓰면 12,760줄이 전부 diff 로 뜨고 **추가한 필드가
    #   그 안에 묻힌다.** 줄끝을 보존해야 diff 가 *"추가된 두 필드"* 만 남는다.
    crlf = b"\r\n" in raw
    eol = b"\r\n" if crlf else b"\n"
    # ⚠️원본은 파일 끝 줄바꿈으로 끝나는데 `json.dumps` 는 안 붙인다. 그 한 줄 때문에
    #   자기시험이 항상 "다르다" 로 나오면 시험이 무의미해진다.
    trailing = eol if raw.endswith(eol) else b""
    dumped = json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8")
    probe = (dumped.replace(b"\n", eol) if crlf else dumped) + trailing
    same_style = (probe == raw)
    print(f"  줄끝: {'CRLF' if crlf else 'LF'} (보존한다)")
    print("=" * 96)
    print("  held-out 관계 -> 13개 통제 어휘")
    print("=" * 96)
    print(f"  파일 {p.name} · 레코드 {len(recs)}")
    print(f"  ★직렬화 왕복이 원본과 바이트 동일: "
          f"{'✅ 그렇다' if same_style else '⚠️ 아니다(들여쓰기·순서가 바뀐다)'}")
    if not same_style:
        print("     -> 그래도 **내용은 보존**된다. 재직렬화 형식만 달라진다.")
        print("        원본은 git 에 있으므로 되돌릴 수 있다.")

    seen, unmapped = {}, []
    hist = {"required": {}, "candidate": {}}
    for r in recs:
        for key, src, dst in (
                ("required", "required_relations_canonical", "required_relations_controlled"),
                ("candidate", "candidate_relations_canonical", "candidate_relations_controlled")):
            v = r.get(src)
            if v is None:
                continue
            lst = v if isinstance(v, list) else [v]
            folded = []
            for x in lst:
                c, why = fold(str(x))
                assert c in CTRL, (x, c)
                seen[str(x)] = c
                if why.startswith("매핑표에 없다"):
                    unmapped.append(str(x))
                hist[key][c] = hist[key].get(c, 0) + 1
                folded.append(c)
            r[dst] = folded if isinstance(v, list) else folded[0]

    # ★★두 열을 **나눠서** 읽는다. 섞으면 지표가 조건을 잰다(함정 40).
    #   `required_*` 는 **정답의 관계**라 전부 진짜 관계다 -> `other` 비율이 매핑 품질을 잰다.
    #   `candidate_*` 는 오답 후보를 포함하므로 `wrong_category`·`function_as_identity` 같은
    #   **위반 유형**이 절반이다 -> 거기서 `other` 가 큰 것은 **설계대로**이지 실패가 아니다.
    print(f"\n  원본 관계 {len(seen)}종")
    for key, label in (("required", "required (정답의 관계 - 매핑 품질은 여기서 잰다)"),
                       ("candidate", "candidate (오답 후보 포함 - 위반 유형이 섞여 있다)")):
        h = hist[key]
        tot = sum(h.values()) or 1
        print(f"\n  == {label}")
        print(f"  {'통제어휘':<16}{'빈도':>8}{'비중':>9}")
        for k, v in sorted(h.items(), key=lambda kv: -kv[1]):
            print(f"  {k:<16}{v:>8}{v / tot:>9.1%}")
    req = hist["required"]
    tot_r = sum(req.values()) or 1
    oth = req.get("other", 0) / tot_r
    print(f"\n  ★판정 지표 = required 의 `other` 비중 {oth:.1%}"
          + ("  ⚠️**40% 를 넘는다** — 매핑이 소극적이다. 표를 다시 볼 것"
             if oth > 0.40 else "  ✅40% 미만"))
    cnd = hist["candidate"]
    print(f"  ⚠️candidate 의 `other` {cnd.get('other', 0) / (sum(cnd.values()) or 1):.1%} 는 "
          f"**판정에 쓰지 않는다** — 위반 유형이 그리로 가는 것이 설계다.")
    if unmapped:
        u = sorted(set(unmapped))
        print(f"\n  ⚠️표에 없어 `other` 로 간 이름 {len(u)}종 — **사람이 본다**")
        for x in u[:20]:
            print(f"      · {x}")
        if len(u) > 20:
            print(f"      · ... 외 {len(u) - 20}종")

    print("\n  🚫`forbidden_relations_canonical` 은 접지 않았다 — "
          "그것은 관계가 아니라 **위반 유형**이다(함정 28).")

    if not a.write:
        print("\n  [dry-run] 아무것도 쓰지 않았다. 적용하려면 --write")
        return 0

    MAPOUT.parent.mkdir(parents=True, exist_ok=True)
    MAPOUT.write_bytes(json.dumps(
        {"controlled_vocab": sorted(CTRL), "mapping": dict(sorted(seen.items())),
         "unmapped_to_other": sorted(set(unmapped)),
         "note": "held-out v2.3 의 required/candidate 만. forbidden 은 위반 유형이라 접지 않는다."},
        ensure_ascii=False, indent=2).encode("utf-8"))
    out = json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8")
    if crlf:
        out = out.replace(b"\n", eol)
    out = out + trailing
    tmp = p.with_suffix(".json.tmp")
    tmp.write_bytes(out)                       # ★encode 먼저, 성공했을 때만 쓴다(함정 35)
    tmp.replace(p)
    print(f"\n  ✅ 필드 추가 완료: {p.name}")
    print(f"  ✅ 매핑표: {MAPOUT.relative_to(ROOT)}")
    print("  ⚠️★채점기는 이 필드를 안 읽는다 — **점수는 바뀌지 않는다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
