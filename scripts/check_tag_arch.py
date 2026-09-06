#!/usr/bin/env python3
"""★★태그가 **주장하는 아키텍처**와 `runs/logs/*.json` 이 **기록한 값**을 대조한다.

## 왜 필요한가 (2026-08-31 실사고 — 3.6 GPU시간 소실)

`run_P052_stage4_recursion_third_seed.bat` 은 *"재귀 자의 세 번째 시드"* 를 뽑으려고
`--tag mC_cla1_ag4_r20_s3` 로 3.6시간을 돌았다. **그런데 명령줄에 `--cla-group 1` 이 없었다.**
`m100R1c` 의 기본값은 `cla_group=2` 이므로 **실제로 학습된 것은 cla2 모델**이다.

    시드 1·2 : cla_group 1 · kv_entries 36 · params 48,755,496 · ce_chunk 2048
    "시드 3" : cla_group **2** · kv_entries **18** · params **48,165,672** · ce_chunk **0**

★**그리고 아무 게이트도 안 잡았다**:

| 게이트 | 왜 못 잡았나 |
|---|---|
| `check_batch_flags` | **없는 플래그를 못 본다** — 있는 것만 검사한다 |
| `check_smoke_fields` | `cla_group` 은 **기록됐다.** 값이 틀렸을 뿐이다 |
| `check_run_registry` | 태그 충돌·중복만 본다. 태그의 **뜻**은 안 본다 |
| `paired_eval` | 시키는 대로 셋을 나란히 찍었다. 셋이 같은 것인지 안 묻는다 |

→ ★**"태그가 주장한다 ≠ 그것이 돈다"** — 함정 37("필드가 기록된다 ≠ 그 경로가 실행된다")의
   한 얼굴이다. 종전 게이트들은 전부 *플래그·필드의 존재*를 봤고, 아무도 **값**을 안 봤다.

⚠️★**이 사고의 비용은 시간이 아니라 판정이었다.** 그 3.6시간이 *"재귀 자가 0.0006 에서
0.0175 로 29배 커졌다"* 라는 **거짓 결론**을 만들 뻔했다. 세 점 중 하나가 다른 모델이었다.

## 무엇을 검사하나

태그를 `_` 로 쪼개 아래 토큰이 나오면 json 의 해당 필드와 대조한다.

    cla{N} -> cla_group == N        ag{N} -> attn_group == N
    g{N}   -> mlp_group == N        r{X}{Y} -> train_repeat == X.Y
    s34    -> sparse34 is True      film  -> mlp_film is True
    nokd   -> kd is False           nc/nockpt -> grad_ckpt is False
    gqafixed/gqalatin/gqarandom -> gqa_pass_schedule
    gps{N} -> gqa_pass_seed == N

**값이 다르면 에러.** 필드가 아예 없으면 **정보**다(그 필드를 안 찍던 시절의 런).

🚫**태그 규약을 여기서 새로 만들지 않는다** — 위 표는 이미 쓰이고 있는 표기를 옮긴 것이고,
   맞지 않는 태그가 나오면 **태그를 고치는 게 아니라 이 표를 고칠지 먼저 판단한다**(함정 34).

torch·GPU 를 쓰지 않는다. json 만 읽는다.

사용:
    python scripts/check_tag_arch.py
    python scripts/check_tag_arch.py --quiet     # 실패만
종료코드 = 에러 개수
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★토큰 -> (json 필드, 기대값 산출). **한 곳에서만 정의한다**(함정 18).
RULES: list[tuple[str, str, object]] = [
    (r"^cla(\d+)$", "cla_group", int),
    (r"^ag(\d+)$", "attn_group", int),
    (r"^g(\d+)$", "mlp_group", int),
    (r"^r(\d)(\d)$", "train_repeat", "rXY"),
    (r"^s34$", "sparse34", True),
    (r"^film$", "mlp_film", True),
    (r"^nokd$", "kd", False),
    (r"^nc$", "grad_ckpt", False),
    (r"^nockpt$", "grad_ckpt", False),
    (r"^gqafixed$", "gqa_pass_schedule", "fixed"),
    (r"^gqalatin$", "gqa_pass_schedule", "latin"),
    (r"^gqarandom$", "gqa_pass_schedule", "random"),
    (r"^gps(\d+)$", "gqa_pass_seed", int),
]

# ★★**인정된 오염 태그** — 이미 결과문서에 원인·파급이 적혀 있는 것.
#   🚫**면제가 아니라 등재**다: 에러 대신 **경고로 매번 인쇄**하고 종료코드에서만 뺀다.
#   ⚠️이렇게 하지 않으면 스위트가 **영구히 빨간불**이 되어 **새 오염을 가린다**(경보 피로).
#   ★여기 넣으려면 **결과문서 번호와 절**을 반드시 함께 적는다 — 근거 없는 면제를 막는다.
# ★★2026-09-02 — **비었다. 오염이 개명으로 해소됐다**(사용자 판단 D1).
#
#   `mC_cla1_ag4_r20_s3` (cla2 인데 cla1 이름) -> **`mC_cla2_ag4_r20_s3`** 로 옮겼다.
#   json 안에 `tag_corrected_from` 을 남겼고, 이제 태그의 주장과 값이 일치한다.
#
#   ⚠️★**이름의 흉터는 남는다**: cla2 계열의 세 번째 시드는 `_s3`(seed 777)이고
#   cla1 계열의 세 번째 시드는 **`_s3b`**(seed 777)다. `b` 가 붙은 것은
#   재시도 런이라서다 — 개명 시점에 `_s3` 자리가 오염 태그에 눌려 있었다.
#
#   🚫**여기를 다시 채울 때의 규칙은 그대로다**: 면제가 아니라 **등재**이고,
#   결과문서 번호와 절을 반드시 함께 적는다. 비워 두는 것이 기본값이다.
KNOWN: dict[str, str] = {}

# ⚠️★**의도적으로 안 넣은 토큰**과 그 이유 — 넣으면 오탐이 난다.
#   d{N}   : `d8_dense` 는 층수인데 `mC_d36_ag4` 는 **방문 수**다. 한 글자가 두 양을 가리킨다(함정 28)
#   e{N}   : `e128` 이 emb_rank 인지 emb_dim 인지 로그마다 다르다
#   k{N}   : `k4` 는 kd_every 인데 KD 를 끈 런에도 이름이 남아 있다
#   s{N}   : `s2`·`s3` 는 시드 **순번**이지 시드 값이 아니다
SKIPPED = "d{N} e{N} k{N} s{N}"


def claims(tag: str):
    """태그가 주장하는 (토큰, 필드, 기대값) 목록."""
    out = []
    for tok in tag.split("_"):
        for pat, field, conv in RULES:
            m = re.match(pat, tok)
            if not m:
                continue
            if conv is int:
                want = int(m.group(1))
            elif conv == "rXY":
                want = float(f"{m.group(1)}.{m.group(2)}")
            else:
                want = conv
            out.append((tok, field, want))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="태그 주장 ↔ json 실제값 대조")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    print("=" * 96)
    print("  태그가 주장하는 아키텍처 ↔ json 이 기록한 값")
    print("=" * 96)

    errs, infos, knowns, n_claim, n_file = [], [], [], 0, 0
    for p in sorted((ROOT / "runs" / "logs").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                  # noqa: BLE001
            continue
        tag = d.get("tag", "")
        if not tag:
            continue
        n_file += 1
        for tok, field, want in claims(tag):
            if field not in d:
                infos.append(f"{tag}  `{tok}` -> `{field}` 필드가 json 에 없다"
                             f" (그 필드를 안 찍던 시절의 런)")
                continue
            n_claim += 1
            act = d[field]
            if isinstance(want, bool):
                same = bool(act) == want
            elif isinstance(want, (int, float)):
                same = float(act) == float(want)
            else:
                same = str(act) == str(want)
            if not same:
                line = (f"{tag}\n         `{tok}` 는 {field}={want} 를 주장하는데 "
                        f"**실제는 {act}** 다 — 이 체크포인트는 이름이 말하는 모델이 아니다")
                (knowns if tag in KNOWN else errs).append(line)

    print(f"\n  로그 {n_file}개 · 대조한 주장 {n_claim}건")
    if knowns:
        print(f"\n  ⚠️★**인정된 오염 {len(knowns)}건** (등재됨 — 종료코드에서 빼지만 매번 인쇄한다)")
        for s in knowns:
            tag = s.split("\n")[0]
            print(f"      · {s}")
            print(f"        근거: {KNOWN[tag]}")
    if infos and not a.quiet:
        print(f"\n  [i] 필드 없음 {len(infos)}건 (판정 아님)")
        for s in infos[:6]:
            print(f"      · {s}")
        if len(infos) > 6:
            print(f"      · ... 외 {len(infos) - 6}건")
    if errs:
        print(f"\n  🚫★★**태그와 실제가 다르다 — {len(errs)}건**")
        for s in errs:
            print(f"      · {s}")
        print("\n  ★이 태그의 수치를 **다른 시드나 팔과 나란히 놓지 말 것.** 다른 모델이다.")
        print("  ★배치를 고칠 때는 **기본값에 기대지 말고 축을 명시**한다 — "
              "`m100R1c` 의 cla_group 기본값은 2 다.")
        return len(errs)

    print("\n  ✅ **새** 오염 없음 — 태그가 주장하는 값이 실제와 일치한다"
          + (f" (인정된 {len(knowns)}건 제외)." if knowns else "."))
    print(f"  ⚠️안 보는 토큰: {SKIPPED} — 한 글자가 두 양을 가리켜 오탐이 난다(함정 28).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
