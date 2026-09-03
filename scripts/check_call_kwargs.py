"""`cli.py` 와 `scripts/` 가 넘기는 인자가 **대상 함수에 실제로 있는지** 정적으로 검사한다.

## 왜 필요한가

**사고 1 — 2026-08-06, 키워드**

`--lora-decay` 를 `train()` 에 전달하려고 `cli.py` 를 문자열 치환으로 고쳤는데,
그 문자열이 **유일하지 않았다** — `prepare()` 호출부에도 같은 꼬리가 있었고
`replace(..., 1)` 이 **첫 번째**(prepare)를 바꿨다. 결과:

    TypeError: prepare() got an unexpected keyword argument 'lora_decay'

**그리고 기존 그물이 전부 통과시켰다**:

| 검사 | 왜 못 잡았나 |
|---|---|
| `py_compile` | **문법은 정상**이다 |
| `check_attrs.py` | `cfg.X` 오타만 본다. 함수 호출 시그니처는 안 본다 |
| `check_batch_flags.py` | `--lora-decay` 는 **파서에 있다**. 이름만 보는 도구다 |
| 스모크 | **`train` 만** 돈다. 깨진 것은 `prepare` 였다 |

**전혀 관련 없는 실험(P037 단계4)이 대신 죽었다.** 사용자가 그걸로 발견했다.

★★**사고 2 — 2026-08-31, 위치인자**(결과 064)

`build_config()` 에 **위치인자를 하나 잘못** 넘겨 **P076 단계0 두 팔이 전멸**했다.
🚫**종전 이 도구는 키워드만 봐서 못 잡았다.** 그리고 그 호출은 `cli.py` 가 아니라
**`scripts/` 안에** 있었다 — 이 도구가 **보던 범위 밖**이었다.

→ ★**2026-09-03 확대(사용자 지시 2D)**: 검사 범위에 **`scripts/*.py` 전체**를 넣고,
**위치인자 개수(arity)** 검사를 추가한다.

## 무엇을 검사하나

`tinylm/cli.py` 와 `scripts/*.py` 안의 `f(...)` 호출 중 **대상 함수를 이 저장소에서
유일하게 찾을 수 있는 것**만 골라 둘을 대조한다:

1. 넘기는 **키워드**가 그 함수의 파라미터에 있는가
2. ★**위치인자 개수**가 그 함수가 받을 수 있는 수를 넘지 않는가

**torch 없이 돈다**(AST 만 쓴다) — 학습이 GPU 를 점유한 중에도 돌릴 수 있다.

⚠️**오탐을 피하려고 다음은 건너뛴다**: 이름이 저장소에 **둘 이상** 정의된 경우 ·
호출 파일이 그 이름을 **import 하지도 정의하지도 않은** 경우 · `*args`/`**kwargs` 를
받는 함수 · 호출에 `*seq`/`**d` **전개가 있는** 경우 · 메서드 호출(`obj.f()`).

사용:
    python scripts/check_call_kwargs.py
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# cli.py 가 부르는 주요 진입 함수 → 정의 파일 (★명시 목록은 유지한다.
# 확대 인덱스가 이름 충돌로 건너뛰더라도 이 여덟 개는 반드시 본다.)
TARGETS = {
    "prepare": "tinylm/data/prepare.py",
    "train": "tinylm/train/trainer.py",
    "evaluate": "tinylm/eval/evaluate.py",
    "compare": "tinylm/eval/compare.py",
    "build_kd_cache": "tinylm/train/kd_cache.py",
    "generate": "tinylm/infer/generate.py",
    "load_model": "tinylm/infer/generate.py",
    "lr_find": "tinylm/train/lr_finder.py",
}


def _sig(node):
    """FunctionDef -> (이름집합, **kwargs?, 최대 위치인자수, *args?)"""
    a = node.args
    names = {p.arg for p in (a.posonlyargs + a.args + a.kwonlyargs)}
    n_pos = len(a.posonlyargs) + len(a.args)
    return names, (a.kwarg is not None), n_pos, (a.vararg is not None)


def params_of(path: Path, fname: str):
    """(파라미터 이름 집합, **kwargs 를 받는가). 못 찾으면 None. ★구 인터페이스 유지."""
    if not path.exists():
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fname:
            names, has_kw, _, _ = _sig(node)
            return names, has_kw
    return None


def build_index():
    """저장소 전체의 최상위 함수 정의 인덱스. ★이름이 둘 이상이면 **버린다**(모호)."""
    idx, dupes = {}, set()
    for sub in ("tinylm", "scripts"):
        for p in sorted((ROOT / sub).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in tree.body:              # ★최상위만 — 중첩 함수는 안 본다
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name in idx:
                        dupes.add(node.name)
                    idx[node.name] = (p, _sig(node))
    for d in dupes:
        idx.pop(d, None)
    return idx, dupes


# ★저장소 모듈로 인정하는 접두사. 여기 없는 곳에서 온 이름은 **검사하지 않는다.**
#   2026-09-03 첫 실행에서 `torch.profiler.profile` 이 `diag_spam_rate.profile` 로
#   잘못 결합돼 오탐 2건이 났다 — **이름만 보고 결합하면 안 된다.**
_REPO_MODS = ("tinylm", "scripts")


def _repo_visible(tree, path):
    """이 파일에서 **저장소 함수로 확실히 결합되는** 이름만 돌려준다.

    인정하는 것 둘뿐이다:
      · 같은 파일 최상위에 `def` 로 있다
      · `from tinylm... import f` / `from <scripts 모듈> import f` 로 왔다
    🚫`import torch` 처럼 **외부에서 온 이름은 제외**한다 — 이름이 겹칠 수 있다.
    """
    script_mods = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    seen = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "")
            root = mod.split(".")[0]
            if node.level and node.level > 0:
                ok = True                                  # 상대 import 는 저장소 안이다
            else:
                ok = root in _REPO_MODS or root in script_mods
            if not ok:
                continue
            for al in node.names:
                if al.asname is None:                      # ★별칭은 결합을 흐린다
                    seen.add(al.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            seen.add(node.name)
    return seen


def scan(path: Path, idx, errs):
    """한 파일의 호출을 검사한다."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return 0
    vis = _repo_visible(tree, path)
    rel = path.relative_to(ROOT).as_posix()
    n = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue                                    # ★메서드 호출은 안 본다
        name = node.func.id
        if name not in idx or name not in vis:
            continue
        _p, (names, has_kw, n_pos, has_var) = idx[name]
        if any(isinstance(x, ast.Starred) for x in node.args):
            continue                                    # *seq 전개 → 개수를 모른다
        n += 1
        if not has_var and len(node.args) > n_pos:
            errs.append((rel, node.lineno,
                         f"{name}() 는 위치인자를 최대 {n_pos}개 받는데 "
                         f"**{len(node.args)}개**를 넘긴다  [{_p.relative_to(ROOT).as_posix()}]"))
        if has_kw:
            continue
        for kw in node.keywords:
            if kw.arg is None:                          # **d 전개
                continue
            if kw.arg not in names:
                errs.append((rel, node.lineno,
                             f"{name}() 에 '{kw.arg}' 파라미터가 없다  "
                             f"[{_p.relative_to(ROOT).as_posix()}]"))
    return n


def main():
    errs = []
    checked = 0

    # ── ① 종전 검사 — cli.py 의 명시 대상 여덟 개(이름 충돌과 무관하게 본다)
    cli = ROOT / "tinylm/cli.py"
    tree = ast.parse(cli.read_text(encoding="utf-8"))
    cache = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
        if name not in TARGETS:
            continue
        if name not in cache:
            cache[name] = params_of(ROOT / TARGETS[name], name)
        info = cache[name]
        if info is None:
            errs.append(("tinylm/cli.py", node.lineno, f"정의를 못 찾음 ({TARGETS[name]})"))
            continue
        names, has_kwargs = info
        if has_kwargs:
            continue
        checked += 1
        for kw in node.keywords:
            if kw.arg is None:
                continue
            if kw.arg not in names:
                errs.append(("tinylm/cli.py", node.lineno,
                             f"{name}() 에 '{kw.arg}' 파라미터가 없다"))

    # ── ② ★2026-09-03 확대 — scripts/ 전체 + cli.py, 인덱스 기반
    idx, dupes = build_index()
    files = [cli] + sorted((ROOT / "scripts").glob("*.py"))
    wide = 0
    for f in files:
        wide += scan(f, idx, errs)

    print("=" * 78)
    print("  호출 인자 정합성 검사 — cli.py + scripts/ (torch 불필요)")
    print("=" * 78)
    print(f"  ① cli.py 명시 대상 {len(cache)}종 · 호출 {checked}건")
    print(f"  ② 인덱스 {len(idx)}개 함수 · 파일 {len(files)}개 · 검사한 호출 {wide}건")
    print(f"     (이름이 둘 이상 정의돼 **건너뛴** 함수 {len(dupes)}개)")
    seen = set()
    for rel, ln, msg in errs:
        k = (rel, ln, msg)
        if k in seen:
            continue
        seen.add(k)
        print(f"  [E] {rel}:{ln}  {msg}")
    print(f"\n총 에러 {len(seen)}건")
    if seen:
        print("★흔한 원인 둘")
        print("  1. **문자열 치환이 유일하지 않은 패턴에 걸렸다**(2026-08-06,")
        print("     `doc_min_chars=a.doc_min_chars)` 가 prepare 와 train 양쪽에 있었다).")
        print("  2. ★**위치인자 순서·개수**(2026-08-31 결과 064 — `build_config()` 하나로")
        print("     P076 단계0 두 팔이 전멸했다).")
    print("주의: `**kwargs`·`*args`·전개·메서드 호출·이름 충돌은 건너뛴다. 정적 검사의 한계다.")
    return 1 if seen else 0


if __name__ == "__main__":
    sys.exit(main())
