"""Session adapter: unchanged gates, explicitly bounded text/hash collectors.

The repository's default codex-safe suite still recursively reads other sessions'
handoff/evidence text in two collectors. Do not edit that shared environment
policy here. Run its original gates, replacing only the control-character input
inventory and final worktree hash inventory with the supplied literal file list.
This is a scoped audit, not a whole-worktree clean claim or filesystem isolation.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def allowed(path):
    value=json.loads(path.read_text(encoding="utf-8"))
    assert value["purpose"]=="P106B_CORPUS_CLEANUP_GOAL_20261026"
    paths=value["paths"]
    assert paths and len(paths)==len(set(paths))
    for raw in paths:
        p=Path(raw)
        assert not p.is_absolute() and ".." not in p.parts and p.as_posix()==raw
        assert p.parts[0] not in {"datasets","data_cache","runs","HF",".git",".aws",".agents",".codex"}
        assert not (ROOT/p).is_symlink()
    return paths


def controls(path):
    import check_control_chars as control
    errors=[];count=0
    for raw in allowed(path):
        target=ROOT/raw
        if target.suffix.lower() not in control.EXTS or not target.exists():continue
        found=control.first_bad_control(target.read_bytes());count+=1
        if found:errors.append(dict(path=raw,byte_offset=found[0],value=found[1]))
    print(json.dumps(dict(check="control_characters",scope="EXPLICIT_SESSION_PATHS_ONLY",
                          files=count,errors=errors),ensure_ascii=False))
    return int(bool(errors))


def main():
    if sys.argv[1]=="controls":return controls(Path(sys.argv[2]))
    scope_path,output,wip=map(Path,sys.argv[1:])
    paths=allowed(scope_path)
    os.environ.update(CUDA_VISIBLE_DEVICES="",TOKENIZERS_PARALLELISM="false")
    spec=importlib.util.spec_from_file_location("original_static",ROOT/"scripts/check_static_all.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original_command=module.command_for_check;original_write=module._write_evidence

    def command(name,argv):
        if name=="check_control_chars":
            return [sys.executable,"-I",str(Path(__file__).resolve()),"controls",str(scope_path.resolve())]
        return original_command(name,argv)

    def manifest(*,evidence_output=None,profile="all"):
        assert profile=="codex-safe"
        records=[]
        for raw in paths:
            target=ROOT/raw
            if evidence_output is not None and target.resolve()==evidence_output.resolve():
                value="SELF_EVIDENCE_OUTPUT"
            else:
                assert target.is_file(),raw
                value=digest(target)
            records.append(dict(status="EXPLICIT_SESSION_SCOPE",path=raw,sha256=value))
        canonical=json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(",", ":"))
        return records,hashlib.sha256(canonical.encode()).hexdigest().upper()

    def write(path,payload):
        payload["execution_scope_adapter"]=dict(
            path=str(Path(__file__).relative_to(ROOT)),sha256=digest(Path(__file__)),
            inventory=str(scope_path),inventory_sha256=digest(scope_path),
            original_suite_sha256=digest(ROOT/"scripts/check_static_all.py"),
            replaced_collectors=["check_control_chars input inventory","worktree hash inventory"],
            unchanged_gate_commands_except_collector=True,whole_worktree_clean_claim=False)
        return original_write(path,payload)

    module.command_for_check=command;module._worktree_manifest=manifest;module._write_evidence=write
    sys.argv=[str(ROOT/"scripts/check_static_all.py"),"--profile","codex-safe","--quiet",
              "--json",str(output),"--wip",str(wip)]
    return module.main()


if __name__=="__main__":raise SystemExit(main())
