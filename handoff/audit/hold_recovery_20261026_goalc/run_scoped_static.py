"""Extend the previous session adapter with an explicitly scoped link reader.

Original validators and their pass criteria are retained. The link filename
candidate index is disabled; it supplies repair hints, not acceptance evidence.
No --fix option is passed. This remains a scoped audit, not filesystem isolation.
"""
from pathlib import Path
import importlib.util
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
PARENT = ROOT / "handoff/audit/source_cleanup_20261026_goalc/run_scoped_static.py"
spec = importlib.util.spec_from_file_location("previous_scoped_static", PARENT)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)


def links(scope):
    import check_links
    metadata = json.loads(scope.read_text(encoding="utf-8"))
    projections = {}
    if metadata.get("owned_shared_changes"):
        record = ROOT / metadata["owned_shared_changes"]
        for item in json.loads(record.read_text(encoding="utf-8"))["shared_files"]:
            payload = Path(item["payload"])
            assert previous.digest(payload) == item["payload_sha256"]
            projections[item["path"]] = payload
    class ExplicitMarkdown(type(Path())):
        def read_text(self, *args, **kwargs):
            raw = self.relative_to(ROOT).as_posix()
            if raw in projections:
                return projections[raw].read_text(*args, **kwargs)
            return super().read_text(*args, **kwargs)
    paths = [ExplicitMarkdown(ROOT / p) for p in previous.allowed(scope) if p.endswith(".md")]
    check_links._targets = lambda: paths
    check_links._index = lambda: {}
    sys.argv = [str(ROOT / "scripts/check_links.py")]
    return check_links.main()


def main():
    if sys.argv[1] == "links":
        return links(Path(sys.argv[2]))
    scope, output, wip = map(Path, sys.argv[1:])
    paths = previous.allowed(scope)
    os.environ.update(CUDA_VISIBLE_DEVICES="", TOKENIZERS_PARALLELISM="false")
    spec = importlib.util.spec_from_file_location("original_static", ROOT / "scripts/check_static_all.py")
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    metadata = json.loads(scope.read_text(encoding="utf-8"))
    additional_not_run = metadata.get("additional_not_run", {})
    assert set(additional_not_run) <= {"check_hf_redirect", "check_smoke_diag"}
    suite.CODEX_SAFE_EXCLUDED = dict(suite.CODEX_SAFE_EXCLUDED, **additional_not_run)
    original_command, original_write = suite.command_for_check, suite._write_evidence

    def command(name, argv):
        if name == "check_control_chars":
            return [sys.executable, "-I", str(PARENT), "controls", str(scope.resolve())]
        if name == "check_links":
            return [sys.executable, "-I", str(Path(__file__).resolve()), "links", str(scope.resolve())]
        return original_command(name, argv)

    def manifest(*, evidence_output=None, profile="all"):
        assert profile == "codex-safe"
        records = []
        for raw in paths:
            path = ROOT / raw
            value = "SELF_EVIDENCE_OUTPUT" if evidence_output and path.resolve() == evidence_output.resolve() else previous.digest(path)
            records.append(dict(status="EXPLICIT_SESSION_SCOPE", path=raw, sha256=value))
        canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return records, previous.hashlib.sha256(canonical.encode()).hexdigest().upper()

    def write(path, payload):
        payload["execution_scope_adapter"] = dict(path=str(Path(__file__).relative_to(ROOT)),
            sha256=previous.digest(Path(__file__)), reused_adapter=str(PARENT.relative_to(ROOT)),
            reused_adapter_sha256=previous.digest(PARENT), inventory=str(scope), inventory_sha256=previous.digest(scope),
            original_suite_sha256=previous.digest(ROOT / "scripts/check_static_all.py"),
            replaced_collectors=["check_control_chars input inventory", "worktree hash inventory", "check_links document inventory and repair-hint index", "optional owned shared-file Markdown projection"],
            unchanged_validation_criteria=True, whole_worktree_clean_claim=False, filesystem_isolation=False)
        payload["execution_scope_adapter"]["additional_not_run"] = additional_not_run
        payload["execution_scope_adapter"]["prior_global_errors_are_not_resolved_by_scoping"] = bool(additional_not_run)
        return original_write(path, payload)

    suite.command_for_check, suite._worktree_manifest, suite._write_evidence = command, manifest, write
    sys.argv = [str(ROOT / "scripts/check_static_all.py"), "--profile", "codex-safe", "--quiet", "--json", str(output), "--wip", str(wip)]
    return suite.main()


if __name__ == "__main__":
    raise SystemExit(main())
