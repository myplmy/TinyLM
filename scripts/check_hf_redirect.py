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

`datasets`·`transformers`·`huggingface_hub`를 import하기 전에 저장소 캐시
초기화가 보장되는지 본다. 모듈 import의 부작용과 명시 초기화 호출을 추적한다.
파일 실행용 루트 부트스트랩은 실제 셸·배치가 파일 경로로 호출하는 진입점에 적용한다.
소스를 AST로 읽으며 라이브러리 import, 모델 로딩, 네트워크 접근은 수행하지 않는다.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HF_LIBS = {"datasets", "transformers", "huggingface_hub"}
CACHE_CONFIG = "scripts.prepare_p106b_official_eval.configure_hf_cache"
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
FILE_ENTRY = re.compile(r"(?:^|[\s\"'/])scripts[/\\]([a-zA-Z0-9_]+\.py)(?=$|[\s\"'])")
REPO_ROOT_EXPRESSIONS = {'Path(__file__).resolve().parent.parent',
                         'Path(__file__).resolve().parents[1]'}


def imports(node):
    """Yield the module loaded and the qualified Python binding it establishes."""
    if isinstance(node, ast.Import):
        for item in node.names:
            binding = item.asname or item.name.split('.')[0]
            yield item.name, binding, item.name if item.asname else binding
    elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
        for item in node.names:
            yield node.module, item.asname or item.name, f"{node.module}.{item.name}"


def qualified(node, names):
    if isinstance(node, ast.Name):
        return names.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        prefix = qualified(node.value, names)
        return f"{prefix}.{node.attr}" if prefix else ""
    return ""


def scan(p: Path):
    """(HF 라이브러리를 쓰는가, tinylm 을 import 하는가)."""
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError as e:                                   # noqa: BLE001
        return None, None, f"파싱 실패: {e}"
    roots = imported_roots(tree)
    return roots & HF_LIBS, "tinylm" in roots, None


def imported_roots(tree):
    return {module.split('.')[0] for node in ast.walk(tree) for module, _, _ in imports(node)}


def _expression_calls(node):
    """Only expressions evaluated before this statement completes normally."""
    if isinstance(node, ast.Call):
        yield node
    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            yield from _expression_calls(element)


class ImportOrder:
    def __init__(self, modules):
        self.modules = modules
        self.module_results = {}
        self.function_results = {}
        self.functions = {name: {n.name: n for n in tree.body if isinstance(n, FUNCTIONS)}
                          for name, tree in modules.items()}

    def module(self, name, visiting):
        if name in self.module_results:
            return self.module_results[name]
        if name not in self.modules or name in visiting:
            return False, {}
        aliases = {}
        ready = self.sequence(self.modules[name].body, False, aliases, name, visiting | {name})
        result = ready, aliases
        self.module_results[name] = result
        return result

    def call_initializes(self, value, aliases, module, visiting):
        for call in _expression_calls(value):
            name = qualified(call.func, aliases)
            owner, _, func = name.rpartition('.')
            owner = owner or module
            if not (function := self.functions.get(owner, {}).get(func)) or (owner, func) in visiting:
                continue
            if f"{owner}.{func}" == CACHE_CONFIG:
                return True
            key = owner, func
            if key not in self.function_results:
                ready, globals_ = self.module(owner, visiting)
                returns = []
                last = self.sequence(function.body, ready, globals_.copy(), owner,
                                     visiting | {key}, returns=returns)
                self.function_results[key] = last and all(returns)
            if self.function_results[key]:
                return True
        return False

    def sequence(self, body, ready, aliases, module, visiting, early=None, returns=None):
        def branch(statements, initialized, names):
            return self.sequence(statements, initialized, names, module, visiting, early, returns)

        for node in body:
            for source, binding, target in imports(node):
                root = source.split('.')[0]
                if root in HF_LIBS and not ready and early is not None:
                    early.add((node.lineno, root))
                if root == 'tinylm':
                    ready = True
                elif root == 'scripts':
                    dependency = target if target in self.modules else source
                    ready |= self.module(dependency, visiting)[0]
                aliases[binding] = target

            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Return)):
                ready = ready or self.call_initializes(node.value, aliases, module, visiting)
                if isinstance(node, ast.Return):
                    if returns is not None:
                        returns.append(ready)
                    return ready
            elif isinstance(node, ast.If):
                yes = branch(node.body, ready, aliases.copy())
                no = branch(node.orelse, ready, aliases.copy())
                ready = yes and no
            elif isinstance(node, ast.Try):
                success_names = aliases.copy()
                success = branch(node.body, ready, success_names)
                outcomes = [branch(node.orelse, success, success_names)]
                outcomes += [branch(h.body, ready, aliases.copy()) for h in node.handlers]
                ready = branch(node.finalbody, all(outcomes), aliases)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                ready = branch(node.body, ready, aliases)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.ClassDef)):
                branch(node.body, ready, aliases.copy())
                if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                    branch(node.orelse, ready, aliases.copy())
            elif isinstance(node, ast.Match):
                for case in node.cases:
                    branch(case.body, ready, aliases.copy())
        return ready

    def early_imports(self, module):
        tree = self.modules[module]
        early = set()
        self.sequence(tree.body, False, {}, module, {module}, early)
        ready, aliases = self.module(module, set())
        for node in ast.walk(tree):
            if isinstance(node, FUNCTIONS):
                self.sequence(node.body, ready, aliases.copy(), module, {module}, early)
        return sorted(early)


def direct_entries(root):
    launchers = [*root.glob('run_*.sh'), *root.glob('run_*.bat'), *root.glob('run_*.ps1')]
    launchers += list((root / 'scripts/batch').glob('*.bat'))
    entries = set()
    for path in launchers:
        if path.is_symlink() or path.stem.endswith('-done'):
            continue
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        for line in lines:
            if not line.strip().lower().startswith(('#', '::', 'rem ', '@rem ')):
                entries.update(FILE_ENTRY.findall(line))
    return entries


def has_direct_bootstrap(tree):
    """The file entry must make the root importable before loading TinyLM."""
    project_imports = [node.lineno for node in tree.body
                       if any(src.split('.')[0] in {'scripts', 'tinylm'}
                              for src, _, _ in imports(node))]
    first_import = min(project_imports, default=float('inf'))
    repo_root = False
    for statement in tree.body:
        if statement.lineno >= first_import:
            break
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ROOT'
                                                      for t in statement.targets):
            repo_root = ast.unparse(statement.value) in REPO_ROOT_EXPRESSIONS
        if isinstance(statement, ast.If) and ast.unparse(statement.test) == 'str(ROOT) not in sys.path':
            choices = statement.body
        else:
            choices = [statement]
        for choice in choices:
            if (repo_root and isinstance(choice, ast.Expr) and isinstance(choice.value, ast.Call)
                    and qualified(choice.value.func, {}) in {'sys.path.insert', 'sys.path.append'}
                    and choice.value.args and ast.unparse(choice.value.args[-1]) == 'str(ROOT)'):
                return True
    return False


def main():
    print("=" * 96)
    print("  HF 캐시 리다이렉트 검사 — `tinylm` import 가 HF 라이브러리보다 먼저인가")
    print("=" * 96)
    errors, modules = [], {}
    for p in sorted(ROOT.glob("scripts/*.py")):
        try:
            modules['scripts.' + p.stem] = ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
        except SyntaxError as error:
            errors.append(f"{p.name}: 파싱 실패: {error}")
    order = ImportOrder(modules)
    entries = direct_entries(ROOT)
    hf_count = direct_count = 0
    for name, tree in modules.items():
        filename = name.rsplit('.', 1)[-1] + '.py'
        roots = imported_roots(tree)
        if filename in entries and (roots & (HF_LIBS | {'tinylm'})):
            direct_count += 1
            if not has_direct_bootstrap(tree):
                errors.append(f"{filename}: 파일 경로 진입점의 루트 부트스트랩이 확인되지 않음")
        if roots & HF_LIBS:
            hf_count += 1
            for line, library in order.early_imports(name):
                errors.append(f"{filename}:{line}: {library} import 전에 프로젝트 캐시 초기화가 확인되지 않음")
    for e in errors:
        print(f"  🚫 {e}")
    print(f"\n  HF 사용 {hf_count}개 · 관련 파일 진입점 {direct_count}개 — 오류 {len(errors)}건")
    print("=" * 96)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
