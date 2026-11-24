#!/usr/bin/env python3
"""정적 속성 검사 — `cfg.<attr>` 이 실제 `TMTConfig` 에 있는지 **torch 없이** 확인한다.

★왜 만들었나 (P029 사고)
  `scripts/probe_prompts.py` 초판이 `cfg.seq_len` 을 썼다. 실제 필드는 `max_seq_len` 이다.
  파이썬은 실행 시점까지 이걸 잡아주지 않고, 그 줄은 **모델을 GPU 에 로드한 뒤**에야 실행되므로
  사용자가 배치를 돌린 다음에야 터졌다.

  더 근본 원인은 **샘플링 루프를 복제한 것**이었다(`generate.py` 에 이미 올바른 구현이 있었다).
  그건 `generate.sample()` 로 합쳐 해결했고, 이 스크립트는 **같은 부류의 오타를 사전에** 잡는다.

  AST 만 쓰므로 **torch·GPU 불필요** = 어디서든 수 초에 돌릴 수 있다.

검사
  `cfg.X` / `config.X` 접근을 TMTConfig 필드와 대조한다. 확인된 사전·외부 설정 클래스·
  설정 모듈 접근에는 해당 객체의 속성을 적용한다.

★한계
  - 정적 분석이라 동적 접근(`getattr(cfg, name)`)은 못 본다.
  - 필드가 **존재**하는지만 본다. 값이 맞는지, 로직이 옳은지는 전혀 모른다.
  - 이걸 통과해도 실행은 실패할 수 있다. **스모크(run_smoke.bat)의 대체가 아니다.**

사용법
  python scripts/check_attrs.py
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = sorted(list((ROOT / "scripts").glob("*.py")) + list((ROOT / "tinylm").rglob("*.py")))
NAMES = {"cfg", "config"}
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
MAPPING_FACTORIES = {"dict", "json.loads", "lm_eval.tasks._yaml_loader.load_yaml",
                     "scripts.diag_p106b_dvlm_pts.read"}
OTHER_TYPES = {
    "tinylm.config": {"TMTConfig", "PRESETS"},
    "tinylm.train.adaptive_masking.PolicyConfig": {"mask_id", "mask_rate", "special_max"},
    "scripts.p107_scaled_optimizer_group.ScaleConfig": {"init_scale"},
    "dict": {"get", "update"},
}


def _scope_nodes(scope):
    pending = list(reversed(tuple(ast.iter_child_nodes(scope))))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, SCOPES):
            pending.extend(reversed(tuple(ast.iter_child_nodes(node))))


def _qualified(node, aliases):
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        owner = _qualified(node.value, aliases)
        if owner:
            return f"{owner}.{node.attr}"
    return None


def _scope_aliases(nodes, outer):
    aliases = outer.copy()
    for node in nodes:
        if isinstance(node, ast.Import):
            for entry in node.names:
                aliases[entry.asname or entry.name.split('.')[0]] = entry.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for entry in node.names:
                aliases[entry.asname or entry.name] = f"{node.module}.{entry.name}"
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            owner = _qualified(node.value, aliases)
            for target in node.targets:
                if isinstance(target, ast.Name) and owner:
                    aliases[target.id] = owner
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Return):
                value = body[0].value
                if isinstance(value, ast.Call) and _qualified(value.func, aliases) == "json.loads":
                    aliases[node.name] = "json.loads"
    return aliases


def _other_attributes(path, scope, nodes, name, aliases):
    stores = [n for n in nodes if isinstance(n, ast.Name) and n.id == name
              and isinstance(n.ctx, ast.Store)]
    if stores:
        values = {}
        for node in nodes:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                values.update((id(target), node.value) for target in targets)
        factories = {_qualified(values[id(n)].func, aliases) if isinstance(values.get(id(n)), ast.Call)
                     else None for n in stores}
        if factories <= MAPPING_FACTORIES:
            return OTHER_TYPES["dict"]
        if len(factories) == 1:
            return OTHER_TYPES.get(next(iter(factories)), set())
        return set()
    if any(isinstance(n, ast.arg) and n.arg == name for n in nodes):
        if any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
               and n.value.id == name for n in nodes):
            return OTHER_TYPES["dict"]
        # Both local and frozen-mask callers pass this API's separate mask policy.
        if (path.name == "diag_p107_lexical_mask_audit.py" and name == "config"
                and getattr(scope, "name", None) == "audit_mntp_bias"
                and aliases.get("PolicyConfig") == "tinylm.train.adaptive_masking.PolicyConfig"):
            return OTHER_TYPES[aliases["PolicyConfig"]]
        return set()
    return OTHER_TYPES.get(aliases.get(name), set())


def unknown_config_attributes(path, tree, known):
    hits = []
    pending = [(tree, {})]
    while pending:
        scope, enclosing_aliases = pending.pop()
        nodes = list(_scope_nodes(scope))
        aliases = _scope_aliases(nodes, enclosing_aliases)
        pending.extend((n, aliases) for n in nodes if isinstance(n, SCOPES))
        unknown = [n for n in nodes if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                   and n.value.id in NAMES and n.attr not in known and not n.attr.startswith("_")]
        allowed = {name: _other_attributes(path, scope, nodes, name, aliases)
                   for name in {n.value.id for n in unknown}}
        hits.extend((n.lineno, n.attr) for n in unknown if n.attr not in allowed[n.value.id])
    return hits


def config_fields():
    """config.py 를 AST 로 읽어 TMTConfig 의 필드명을 모은다(torch import 없이)."""
    src = (ROOT / "tinylm" / "config.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "TMTConfig":
            out = set()
            for st in node.body:
                if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                    out.add(st.target.id)
                elif isinstance(st, ast.Assign):
                    for t in st.targets:
                        if isinstance(t, ast.Name):
                            out.add(t.id)
                elif isinstance(st, ast.FunctionDef):
                    out.add(st.name)
            return out
    return set()


# 런타임에 붙는 속성(코드에서 cfg.X = ... 로 설정) — 선언 필드가 아니어도 정상
RUNTIME_OK = set()


def collect_runtime_assigned():
    """`cfg.X = ...` 처럼 코드가 나중에 붙이는 속성을 수집(정상으로 취급)."""
    found = set()
    for f in TARGETS:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                            and t.value.id in NAMES):
                        found.add(t.attr)
    return found


def main():
    fields = config_fields()
    if not fields:
        print("[!] TMTConfig 를 파싱하지 못했습니다.")
        return 1
    runtime = collect_runtime_assigned()
    known = fields | runtime | RUNTIME_OK
    print(f"TMTConfig 선언 필드 {len(fields)}개 + 런타임 부착 {len(runtime)}개 = 허용 {len(known)}개\n")

    bad = 0
    for f in TARGETS:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[!] {f.relative_to(ROOT)} 파싱 실패: {e}")
            continue
        hits = unknown_config_attributes(f, tree, known)
        if hits:
            bad += len(hits)
            print(f"  [E] {f.relative_to(ROOT)}")
            for ln, at in sorted(set(hits)):
                near = [k for k in sorted(known)
                        if k.startswith(at[:4]) or at in k or k in at]
                hint = f"   (혹시 이것? {', '.join(near[:3])})" if near else ""
                print(f"        L{ln}: cfg.{at} — TMTConfig 에 없음{hint}")

    print(f"\n총 {bad}건")
    print("주의: 정적 검사라 getattr() 같은 동적 접근은 못 본다. 필드 '존재'만 보고 값·로직은 모른다.")
    print("      스모크(run_smoke.bat)의 대체가 아니라 그 앞단의 값싼 그물이다.")
    return int(bool(bad))


if __name__ == "__main__":
    sys.exit(main())
