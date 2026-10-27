"""Original static criteria with this session's explicit text/hash inventory.

No shared checker is edited. Other checks keep their original commands. This
is not whole-worktree cleanliness, OS isolation, or a model-quality gate.
"""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import importlib.util
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"scripts"))
PURPOSE = "OCT27_INDEPENDENT_EXPERIMENT_SCOPE_V1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def paths(scope):
    data = json.loads(scope.read_text(encoding="utf-8"))
    assert data["purpose"] == PURPOSE
    names = data["paths"]
    assert names and len(names) == len(set(names))
    blocked = {"datasets", "data_cache", "runs", "HF", "agents", ".git", ".aws", ".agents", ".codex"}
    for raw in names:
        name = Path(raw)
        assert not name.is_absolute() and ".." not in name.parts and name.as_posix() == raw
        assert name.parts[0] not in blocked
        candidate = ROOT/name
        assert candidate.is_file() and not any(p.is_symlink() for p in (candidate, *candidate.parents))
    return names


def text_check(kind, scope):
    names = paths(scope)
    if kind == "controls":
        import check_control_chars as original
        candidates = [ROOT/name for name in names if Path(name).suffix.lower() in original.EXTS]
        original._targets = lambda: candidates
    else:
        import check_links as original
        candidates = [ROOT/name for name in names if name.endswith(".md")]
        original._targets = lambda: candidates
        # The index only supplies repair suggestions; do not recursively read
        # another session's tree to offer them. Actual link checks are unchanged.
        original._index = lambda: {}
    sys.argv = [str(Path(original.__file__))]
    return original.main()


def main():
    if sys.argv[1] in ("controls", "links"):
        return text_check(sys.argv[1], Path(sys.argv[2]))
    scope, output, wip = map(Path, sys.argv[1:])
    assert not output.exists(), "new versioned static evidence only"
    names = paths(scope)
    before = {name: digest(ROOT/name) for name in names}
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false")
    spec = importlib.util.spec_from_file_location("original_static", ROOT/"scripts/check_static_all.py")
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    command_for_check, write_evidence = suite.command_for_check, suite._write_evidence

    def command(name, argv):
        if name in ("check_control_chars", "check_links"):
            mode = "controls" if name == "check_control_chars" else "links"
            return [sys.executable, "-I", str(Path(__file__).resolve()), mode, str(scope.resolve())]
        return command_for_check(name, argv)

    def manifest(*, evidence_output=None, profile="all"):
        assert profile == "codex-safe"
        records = [dict(status="EXPLICIT_SESSION_SCOPE", path=name, sha256=digest(ROOT/name)) for name in names]
        data = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return records, hashlib.sha256(data).hexdigest().upper()

    def write(path, payload):
        changed = [name for name in names if digest(ROOT/name) != before[name]]
        payload["execution_scope_adapter"] = dict(path=str(Path(__file__).relative_to(ROOT)),
            sha256=digest(Path(__file__)), inventory=str(scope), inventory_sha256=digest(scope),
            original_suite_sha256=digest(ROOT/"scripts/check_static_all.py"),
            replaced_collectors=["control text inventory", "link document inventory and repair suggestions", "hash inventory"],
            unchanged_validation_criteria=True, extra_not_run_checks=[],
            whole_worktree_clean_claim=False, filesystem_isolation=False,
            declared_inputs_unchanged=not changed, changed_inputs=changed)
        return write_evidence(path, payload)

    suite.command_for_check, suite._worktree_manifest, suite._write_evidence = command, manifest, write
    sys.argv = [str(ROOT/"scripts/check_static_all.py"), "--profile", "codex-safe", "--quiet",
        "--json", str(output), "--wip", str(wip)]
    raw_log = output.with_suffix(".log")
    with raw_log.open("x", encoding="utf-8") as stream, redirect_stdout(stream), redirect_stderr(stream):
        result = suite.main()
    audit = json.loads(output.read_text(encoding="utf-8"))
    print(json.dumps(dict(actual_suite_returncode=result, counts=audit["counts"], raw_log=str(raw_log),
        failures=[row["name"] for row in audit["checks"] if row["status"] == "ERROR"])))
    changed = [name for name in names if digest(ROOT/name) != before[name]]
    if changed:
        print(json.dumps(dict(status="AUDIT_DECLARED_INPUTS_CHANGED", paths=changed)))
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
