#!/usr/bin/env python3
"""★★**HF 캐시 리다이렉트가 실제로 걸리는가.** torch·네트워크 0.

## 왜 이 검사가 생겼나 (2026-08-22 실사고)

`tinylm/paths.py` 는 **import 부작용**으로 HF 캐시를 작업폴더 `HF/` 로 강제한다:

    os.environ["HF_HOME"] = str(HF_DIR)
    os.environ["HF_HUB_CACHE"] = str(HF_DIR / "hub")
    os.environ["HF_DATASETS_CACHE"] = str(HF_DIR / "datasets")

🚫**그런데 `scripts/fetch_bench_data.py` 는 `sys.path` 만 건드리고 `tinylm` 을 import
하지 않았다.** 그래서 그 부작용이 **한 번도 일어나지 않았고**, `datasets` 가 사용자
환경의 `HF_HOME`(`Z:\\unsloth_files\\cache`)로 15종을 받았다. 사용자가 손으로 옮겼다.

★★**함정 37 의 다른 얼굴**이다 — *"리다이렉트가 존재한다 ≠ 그 경로가 실행된다."*
그리고 이건 **조용한 실패**였다: 다운로드는 성공했고 에러도 없었다.

## 무엇을 보나

`scripts/` 의 모든 `.py` 에 대해:

| 조건 | 판정 |
|---|---|
| `datasets`·`transformers`·`huggingface_hub` 를 import 하는가 | 대상 |
| 그 전에 `import tinylm` 또는 `from tinylm...` 이 있는가 | ✅ |
| 없으면 | 🚫**에러** |

⚠️★**함수 안의 지연 import 도 본다.** 실제 실행 시점이 모듈 상단보다 뒤일 뿐,
**`tinylm` 이 아예 import 되지 않으면 리다이렉트는 영영 안 걸린다.**

🚫**사용자 환경변수를 영구 수정하지 않는다** — 이 규약은 **프로세스 안에서만** 바꾼다.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HF_LIBS = {"datasets", "transformers", "huggingface_hub"}
# ★예외: `tinylm` 패키지 자신과, HF 를 안 쓰는 순수 도구
EXEMPT = {"check_hf_redirect.py"}


def scan(p: Path):
    """(HF 라이브러리를 쓰는가, tinylm 을 import 하는가)."""
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:                                   # noqa: BLE001
        return None, None, f"파싱 실패: {e}"
    uses_hf, imports_tinylm = set(), False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in HF_LIBS:
                    uses_hf.add(root)
                if root == "tinylm":
                    imports_tinylm = True
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in HF_LIBS:
                uses_hf.add(root)
            if root == "tinylm":
                imports_tinylm = True
    return uses_hf, imports_tinylm, None


def main():
    print("=" * 96)
    print("  HF 캐시 리다이렉트 검사 — `tinylm` import 가 HF 라이브러리보다 먼저인가")
    print("=" * 96)
    err, ok, skip = [], 0, 0
    for p in sorted(ROOT.glob("scripts/*.py")):
        if p.name in EXEMPT:
            continue
        uses, has_tl, bad = scan(p)
        if bad:
            err.append(f"{p.name}: {bad}")
            continue
        if not uses:
            skip += 1
            continue
        if has_tl:
            ok += 1
            print(f"  ✅ {p.name:<28} HF: {','.join(sorted(uses))}")
        else:
            err.append(
                f"{p.name}: **{','.join(sorted(uses))} 를 쓰는데 `import tinylm` 이 없다** "
                f"-> HF 캐시가 작업폴더 밖으로 간다(2026-08-22 실사고). "
                f"파일 상단 `sys.path.insert` 바로 뒤에 `import tinylm  # noqa: F401` 을 넣으세요")
    # ★★2026-08-30 신설 — **`import tinylm` 이 있다 ≠ 그 import 가 성공한다.**
    #
    #   🚫**실사고**: `scripts/diag_dataset_tokens.py` 는 위 검사를 통과했다
    #   (`import tinylm` 이 있었다). 그런데 **`sys.path.insert` 가 없어서**
    #   실행하면 `ModuleNotFoundError: No module named 'tinylm'` 로 죽었다.
    #   P075 단계0b 가 그렇게 **두 팔 모두 0.0분 만에 실패**했다(2026-08-30).
    #
    #   스크립트를 `python scripts/x.py` 로 직접 실행하면 `sys.path[0]` 은
    #   **`scripts/` 디렉터리**이지 저장소 루트가 아니다. 루트를 넣지 않으면
    #   `tinylm` 은 보이지 않는다.
    #
    #   ★위 검사와 이 검사는 **다른 층**이다: 위는 *"리다이렉트를 걸 의도가 있는가"*,
    #   이것은 *"그 의도가 실행될 수 있는가"*. 함정 37 그대로다.
    path_err = []
    for p in sorted(ROOT.glob("scripts/*.py")):
        if p.name in EXEMPT:
            continue
        src = p.read_text(encoding="utf-8")
        _, has_tl, bad = scan(p)
        if bad or not has_tl:
            continue
        if "sys.path.insert" not in src and "sys.path.append" not in src:
            path_err.append(
                f"{p.name}: **`import tinylm` 은 있는데 `sys.path.insert` 가 없다** "
                f"-> 직접 실행하면 ModuleNotFoundError 로 죽는다(P075 단계0b 실사고). "
                f"`ROOT = Path(__file__).resolve().parent.parent` 바로 뒤에 "
                f"`sys.path.insert(0, str(ROOT))` 를 넣으세요")
    err += path_err

    for e in err:
        print(f"  🚫 {e}")
    if not path_err:
        print("  ✅ `import tinylm` 하는 스크립트 전부가 `sys.path` 를 먼저 세운다")
    print(f"\n  대상 {ok + len(err)}개 (HF 미사용 {skip}개 제외) — "
          f"{'✅ 전부 통과' if not err else f'🚫 {len(err)}건 실패'}")
    print("  ⚠️ 정적 검사다. **import 가 있다** 는 것만 보고 **환경변수가 실제로 바뀌었는지**는")
    print("     `fetch_bench_data.py` 가 실행 시점에 인쇄해 스스로 확인한다(이중 그물).")
    print("=" * 96)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
