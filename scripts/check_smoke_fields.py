"""정적 게이트 20 — **스모크가 요구하는 계측 필드를 trainer 가 정말 찍는가.**

★왜 생겼나 (2026-08-30, 스모크 에러 1건)
    `sm_film` 팔이 `[E] mlp_film = None (기대 True)` 로 죽었다. 원인은 아키텍처도
    플래그도 아니었다 — **`tinylm/train/trainer.py` 의 결과 json 딕셔너리에
    `mlp_film` 키가 아예 없었다.** `--mlp-film` 은 2026-07 부터 있었고 실런도
    둘(`mC_film`·`t_film`) 있는데, **json 만 보면 FiLM 런과 아닌 런이 구분되지 않았다.**

    같은 계열의 선례가 이미 둘 있다.
        `kd_alpha`/`kd_temp`  2026-08-20  배치 꼬리말이 *"json 에서 확인하라"* 고
                                          적었는데 **필드 자체가 없었다**
        `emb_init`            자백 A13    `mC_e128`(난수) vs `mC_e128svd`(SVD)가
                                          **json 으로 구분되지 않았다**

    세 번 같은 형태로 났으므로 **규약이 아니라 게이트로 막는다.**

★게이트 15 와 무엇이 다른가
    게이트 15(`check_smoke_coverage`)는 **"배치가 켜는 축을 스모크가 켜는가"** —
    *플래그* 단위다. 이 게이트는 **"스모크가 요구하는 필드를 trainer 가 찍는가"** —
    *필드* 단위다. 15 를 통과해도 여기서 죽을 수 있고, 이번이 정확히 그 경우였다.

무엇을 보나
    `scripts/check_smoke.py` 의 `REQUIRED` + `EXPECT` 키 전부를 모아,
    `tinylm/train/trainer.py` 의 `res = {...}` 가 실제로 그 키를 만드는지 본다.
    `**_memall` 같은 언팩은 **생산 함수까지 따라가서** 키를 모은다.

    ⚠️**한계** — 이 게이트는 *"키가 딕셔너리에 있는가"* 만 본다.
    🚫**그 값이 옳은지, 그 코드 경로가 실제로 도는지는 보지 않는다**(함정 37).
    동적 스모크가 그것을 산다. **정적은 동적을 대체하지 않는다.**

    python scripts/check_smoke_fields.py
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_CHK = ROOT / "scripts" / "check_smoke.py"
TRAINER = ROOT / "tinylm" / "train" / "trainer.py"
PKG = ROOT / "tinylm"

# ★스모크가 안 보는데 trainer 가 찍는 키는 이 게이트의 관심 밖이다.
#   반대(스모크가 요구하는데 trainer 가 안 찍는 것)만 본다.


def _dict_str_keys(node: ast.AST) -> set[str]:
    """Dict 노드에서 **문자열 리터럴 키**만 모은다."""
    if not isinstance(node, ast.Dict):
        return set()
    return {k.value for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)}


def _returned_keys(fn: ast.AST, depth: int = 0) -> set[str]:
    """함수 본문의 모든 `return {...}` 에서 문자열 키를 모은다.

    ★`return {..., **kv}` 처럼 **반환 안에서 다시 언팩**하는 경우를 따라간다.
    `mem_report_all()` 이 정확히 그 모양이고, 여기서 `kv_entries`·`kv_mb` 가 나온다.
    """
    ks: set[str] = set()
    if fn is None or depth > 4:
        return ks
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
            ks |= _dict_str_keys(n.value)
            for k, v in zip(n.value.keys, n.value.values):
                if k is None:                       # `**something`
                    ks |= _unpack_keys(v, fn, depth + 1)
    return ks


def _unpack_keys(v: ast.AST, scope: ast.AST, depth: int) -> set[str]:
    """`**v` 의 원천 함수를 찾아 그 반환 키를 모은다. 못 찾으면 빈 집합."""
    fname = None
    if isinstance(v, ast.Call):
        fname = getattr(v.func, "id", None) or getattr(v.func, "attr", None)
    elif isinstance(v, ast.Name) and scope is not None:
        for m in ast.walk(scope):                   # 같은 스코프의 `x = f(...)`
            if isinstance(m, ast.Assign) and \
                    any(getattr(t, "id", "") == v.id for t in m.targets) and \
                    isinstance(m.value, ast.Call):
                fname = getattr(m.value.func, "id", None) or \
                    getattr(m.value.func, "attr", None)
                break
    if not fname:
        return set()
    return _find_method_anywhere(fname, depth)


def _find_func(tree: ast.AST, name: str):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return n
    return None


def _find_method_anywhere(name: str, depth: int = 0) -> set[str]:
    """패키지 전체에서 같은 이름의 함수/메서드를 찾아 반환 딕셔너리 키를 모은다.

    ★`model.mem_report_all()` 처럼 **다른 파일의 메서드**를 언팩하는 경우를 위한 것이다.
    동명이인이 있으면 **합집합**을 쓴다 — 이 게이트는 *"없다"* 를 잡는 것이므로
    넓게 잡는 쪽이 **오탐을 만들지 않는다**(함정 34: 오탐이 나면 기준값을 먼저 의심하게 된다).
    """
    ks: set[str] = set()
    for p in sorted(PKG.rglob("*.py")):
        try:
            t = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        fn = _find_func(t, name)
        if fn is not None:
            ks |= _returned_keys(fn, depth)
    return ks


def emitted_keys() -> tuple[set[str], set[str]]:
    """trainer 가 만드는 결과 json 의 키 집합. (확정, 미해결언팩원천)"""
    tree = ast.parse(TRAINER.read_text(encoding="utf-8"))
    keys: set[str] = set()
    unresolved: set[str] = set()

    for n in ast.walk(tree):
        # res = { ... }
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict) \
                and any(getattr(t, "id", "") == "res" for t in n.targets):
            d = n.value
            keys |= _dict_str_keys(d)
            for k, v in zip(d.keys, d.values):
                if k is not None:
                    continue                      # 리터럴 키는 위에서 처리했다
                got = _unpack_keys(v, tree, 0)    # `**something` — 원천을 따라간다
                if got:
                    keys |= got
                else:
                    unresolved.add(ast.unparse(v)[:48])
        # res["tag"] = ...
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and getattr(t.value, "id", "") == "res" \
                        and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
                    keys.add(t.slice.value)
    return keys, unresolved


def wanted_keys() -> tuple[set[str], dict[str, str]]:
    """check_smoke 가 요구하는 키. (전체, 키 -> 출처)"""
    tree = ast.parse(SMOKE_CHK.read_text(encoding="utf-8"))
    want: set[str] = set()
    src: dict[str, str] = {}
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign):
            continue
        names = [getattr(t, "id", "") for t in n.targets]
        if "REQUIRED" in names and isinstance(n.value, (ast.List, ast.Tuple, ast.Set)):
            for e in n.value.elts:
                if isinstance(e, ast.Constant) and isinstance(e.value, str):
                    want.add(e.value)
                    src.setdefault(e.value, "REQUIRED")
        if "EXPECT" in names and isinstance(n.value, ast.Dict):
            for arm, body in zip(n.value.keys, n.value.values):
                armname = arm.value if isinstance(arm, ast.Constant) else "?"
                for k in _dict_str_keys(body):
                    want.add(k)
                    src.setdefault(k, f"EXPECT[{armname}]")
    return want, src


def main() -> int:
    want, src = wanted_keys()
    have, unresolved = emitted_keys()
    missing = sorted(want - have)

    print("=" * 78)
    print("정적 게이트 20 — 스모크 요구 필드 vs trainer 가 찍는 필드")
    print("=" * 78)
    print(f"  check_smoke 가 요구하는 키 : {len(want)}개")
    print(f"  trainer res 가 만드는 키   : {len(have)}개")
    if unresolved:
        print(f"  ⚠️따라가지 못한 언팩 원천  : {sorted(unresolved)}")
        print("     → 그 원천이 만드는 키는 이 게이트가 보증하지 못한다.")

    if not missing:
        print("\n[OK] 요구 필드가 전부 trainer 의 결과 딕셔너리에 있다.")
        print("     ⚠️단 '키가 있다' 이지 '값이 옳다' 도 '그 경로가 돈다' 도 아니다(함정 37).")
        return 0

    print(f"\n[E] trainer 가 안 찍는 요구 필드 {len(missing)}개")
    for k in missing:
        print(f"    - {k:22s} (요구처: {src.get(k, '?')})")
    print("\n  고치는 곳: tinylm/train/trainer.py 의 `res = {...}`")
    print("  ★이 상태로 긴 런을 돌리면 **결과를 기계로 읽을 수 없는 로그**가 남는다.")
    print("    kd_alpha(2026-08-20)·emb_init(자백 A13)·mlp_film(2026-08-30)이 같은 사고였다.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
