"""Shared, versioned contracts for authorized isolated Codex smoke execution.

Canonical smoke commands and field criteria remain owned by their existing
modules. This module never imports torch or opens model/dataset payloads.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import shlex

NEW_SCHEMA = "TINYLM_CODEX_SMOKE_EXECUTION_V1"
NEW_PROFILE_ID = "codex_isolated_smoke_v1"
NEW_DRIVER = "scripts/codex_smoke.py"
CODEX_CHECKER = ".agents/skills/session-handoff/scripts/check_handoff_codex.py"
CONTRACT_MODULE = "scripts/smoke_execution_contract.py"
CANONICAL_SOURCE = "scripts/batch/tool_smoke.bat"
SESSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
HISTORICAL_DRIVER = "scripts/p106b_relation_smoke.py"
HISTORICAL_RUNTIME = "test_result/evidence/local/p106b_relation_bind_v1_s1337/smoke_20261019"
HISTORICAL_RAW = "smoketest_logs/202610190118_smoke_6ada839.txt"
HISTORICAL_DRIVER_SHA = "BDE14B56E0B16CF821EA32D817F2B21E40A3FA3736C51128AAD5AD78AD06863A"
HISTORICAL_RAW_SHA = "C6072DB0B840A4136C0EA26066A3FBF431A210D0578547B3DF805C664F65FAFA"
HISTORICAL_ISOLATION_SHA = "C1770A2BA618A4B42F948E141FF0044E297BB6A853E6BD41A5BD2A89528935A1"
CODEX_ITEMS = ("CHECK handoff/", "PASS static structure and local links",
               "SUMMARY files=1 errors=0")
SHA_RE = re.compile(r"[0-9A-F]{64}")


def _regular(path: Path) -> Path:
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"regular nonlinked file required: {path}")
    return path


def file_sha256(path: Path, *, guard=None) -> str:
    if guard is not None:
        guard()
    digest = hashlib.sha256()
    with _regular(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            if guard is not None:
                guard()
            digest.update(block)
    if guard is not None:
        guard()
    return digest.hexdigest().upper()


def _no_links(root: Path, path: Path) -> None:
    relative = path.relative_to(root)
    current = root
    for part in (None, *relative.parts):
        if part is not None:
            current = current / part
        if current.is_symlink():
            raise ValueError("linked smoke destination/source forbidden")


def destinations(repo_root: Path, session_id: str) -> dict:
    if type(session_id) is not str or SESSION_RE.fullmatch(session_id) is None:
        raise ValueError("one safe explicit smoke session identifier required")
    root = Path(repo_root).absolute()
    if root.is_symlink():
        raise ValueError("linked repository root forbidden")
    runtime = root / "runs" / "validation" / "codex_smoke" / session_id
    evidence = root / "test_result" / "evidence" / "codex_smoke" / session_id
    report = evidence / "smoke_report.json"
    for path in (runtime, evidence, report, root / "smoketest_logs"):
        _no_links(root, path)
    return dict(runtime=runtime, evidence=evidence, report=report,
                log_name="smoke_codex_" + session_id)


def adapt_actions(actions, *, driver: str, contract_args):
    if (type(driver) is not str or not driver.startswith("scripts/")
            or not driver.endswith(".py") or ".." in Path(driver).parts
            or type(contract_args) not in (list, tuple)
            or any(type(value) is not str for value in contract_args)):
        raise ValueError("explicit approved driver/contract argv required")
    adapted, changes = [], []
    for action in actions:
        before = list(action.argv)
        after = list(before)
        if action.kind == "run" and "--" in before:
            at = before.index("--")
            child = before[at + 1:]
            kind = None
            if len(child) == 2 and child[1] == "scripts/check_handoff.py":
                after[at + 1:] = [child[0], "-I", "-B", CODEX_CHECKER]
                kind = "codex_document_checker"
            elif len(child) == 2 and child[1] == "scripts/check_smoke.py":
                after[at + 1:] = [child[0], driver, *contract_args]
                kind = "isolated_field_log_path"
            if kind:
                changes.append(dict(line=action.line, kind=kind,
                                    before=before, after=after))
        adapted.append(replace(action, argv=tuple(after)))
        if (action.kind == "run" and "run100m.py" in before
                and before != after):
            raise ValueError("canonical training argv must remain identical")
    if [edit["kind"] for edit in changes] != [
            "codex_document_checker", "isolated_field_log_path"]:
        raise ValueError("exactly the document and field-path adaptations required")
    return adapted, changes


def execution_source_pins(repo_root: Path, *, guard=None) -> dict[str, str]:
    """Hash only bounded source files; never traverse checkpoints or datasets."""
    if guard is not None:
        guard()
    root = Path(repo_root).absolute()
    _no_links(root, root)
    _no_links(root, root / CANONICAL_SOURCE)
    from scripts.smoke_module import parse_smoke_module
    names = {
        CANONICAL_SOURCE, NEW_DRIVER, CONTRACT_MODULE, CODEX_CHECKER,
        "scripts/runlog.py", "scripts/smoke_module.py",
        "scripts/summarize_smoke.py", "scripts/check_smoke.py",
        "scripts/smoke_diag_contract.tsv",
    }
    for action in parse_smoke_module(root / CANONICAL_SOURCE):
        if guard is not None:
            guard()
        for value in action.argv:
            if value.endswith(".py"):
                path = Path(value)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("source script must be repository relative")
                names.add(path.as_posix())
    source_tree = root / "tinylm"
    _no_links(root, source_tree)
    if source_tree.exists():
        directories = [source_tree]
        while directories:
            if guard is not None:
                guard()
            directory = directories.pop()
            _no_links(root, directory)
            for path in sorted(directory.iterdir()):
                if guard is not None:
                    guard()
                _no_links(root, path)
                if path.is_dir():
                    directories.append(path)
                elif path.suffix == ".py":
                    names.add(path.relative_to(root).as_posix())
    pins = {}
    for name in sorted(names):
        if guard is not None:
            guard()
        path = root / name
        _no_links(root, path)
        pins[name] = file_sha256(path, guard=guard)
    return pins


def modern_profiles():
    """One bounded historical profile and one reusable future schema."""
    return (
        ("p106b_relation_bind_v1_s1337/smoke_20261019", HISTORICAL_DRIVER,
         "HISTORICAL_RELATION_SMOKE_20261019", "smoke"),
        ("codex_smoke", NEW_DRIVER, NEW_SCHEMA, "smoke_codex_"),
    )


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _integer(value, expected, name):
    _require(type(value) is int and value == expected, name + " mismatch")


def _json_source(root, path):
    _no_links(root, path)
    raw = _regular(path).read_bytes()
    _require(len(raw) < 20_000_000, "oversized adaptation receipt")
    data = json.loads(raw.decode("utf-8"))
    _require(type(data) is dict, "adaptation receipt must be an object")
    return data


def _argv(value):
    _require(type(value) is list and bool(value)
             and all(type(part) is str for part in value), "invalid recorded argv")
    return value


def _with_interpreter(actions, interpreter):
    _require(type(interpreter) is str and bool(interpreter)
             and not any(char in interpreter for char in "\r\n\0"),
             "one explicit recorded interpreter required")
    result = []
    for action in actions:
        argv = list(action.argv)
        if action.kind == "run":
            argv[0] = interpreter
            if "--" in argv:
                argv[argv.index("--") + 1] = interpreter
        result.append(replace(action, argv=tuple(argv)))
    return result


def _manifest(actions):
    return [dict(kind=action.kind, line=action.line, argv=list(action.argv),
                 seconds=action.seconds) for action in actions]


def _validate_actual_blocks(log, records, actions, interpreter, summary):
    """Check real closed raw blocks independently of writer receipts."""
    text = _regular(log).read_text(encoding="utf-8", errors="strict")
    _require(len(re.findall(r"^\[runlog\] cmd=", text, re.M)) == len(records),
             "unclosed/overlapping raw command block")
    _require(len(re.findall(r"^\[runlog\] 종료코드 -?\d+\s", text, re.M)) == len(records),
             "missing/extra raw exit footer")
    children = [action for action in actions
                if action.kind == "run" and "--" in action.argv]
    _require(len(records) == len(children) + 1,
             "missing/duplicate child or summary blocks")
    positions = {}
    for index, (action, record) in enumerate(zip(children, records)):
        command, _, code = record
        expected = list(action.argv[action.argv.index("--") + 1:])
        _require(shlex.split(command.replace("\\", "/")) == expected,
                 "actual child argv/order mismatch")
        _integer(code, 0, "actual child exit")
        if CODEX_CHECKER in expected:
            positions["check_handoff.py"] = index
        if NEW_DRIVER in expected or HISTORICAL_DRIVER in expected:
            positions["check_smoke.py"] = index
    command, body, code = records[-1]
    _require(shlex.split(command.replace("\\", "/")) == summary,
             "actual summary argv mismatch")
    _integer(code, 0, "actual summary exit")
    _require(all(marker in body for marker in
                 ("스모크 종료코드 요약", "실패 0개", "총 에러 0건")),
             "summary success markers missing")
    _require(set(positions) == {"check_handoff.py", "check_smoke.py"},
             "exactly two actual adaptations required")
    return {name: (records[index][1], records[index][2],
                   CODEX_ITEMS if name == "check_handoff.py" else None)
            for name, index in positions.items()}


def _snapshot_map(value):
    _require(type(value) is dict, "synthetic snapshot must be a map")
    allowed = re.compile(
        r"(?:runs/(?:ckpt/tiny_synthetic_[A-Za-z0-9_.-]+\.pt|"
        r"logs/tiny_synthetic_[A-Za-z0-9_.-]+\.json)|"
        r"data_cache/synthetic_[A-Za-z0-9_.-]+/(?:train\.bin|val\.bin|meta\.json))")
    _require(all(type(key) is str and allowed.fullmatch(key)
                 and type(sha) is str and SHA_RE.fullmatch(sha)
                 for key, sha in value.items()), "snapshot path/hash is outside synthetic scope")


def _successful_process_state(receipt):
    """A successful receipt cannot also describe uncertain launch/cleanup."""
    _require(receipt.get("process_started") is True
             and receipt.get("creation_attempted") is True
             and receipt.get("launch_state") == "OWNED"
             and receipt.get("unsafe_process_state") is False
             and receipt.get("interrupted_during_cleanup") is False
             and receipt.get("launch_restore_interrupted") is False
             and receipt.get("launch_handler_errors") == []
             and receipt.get("deferred_launch_signals") == []
             and receipt.get("termination") == []
             and type(receipt.get("cleanup_duration_sec")) in (int, float)
             and receipt["cleanup_duration_sec"] == 0,
             "contradictory/unknown process launch or cleanup state")
    ignored = receipt.get("preserved_ignored_launch_signals")
    _require(type(ignored) is list and all(type(sig) is int and sig in (2, 15) for sig in ignored)
             and len(ignored) == len(set(ignored)), "invalid preserved ignored signal state")


def validate_modern_adaptation(root, batch, log, records):
    """Return None for legacy/canonical logs, otherwise validated aliases.

    Static only: source/raw/receipt reads, never original model/data snapshots.
    Historical alias acceptance does not invent missing preservation evidence.
    """
    root, batch, log = Path(root).absolute(), Path(batch).absolute(), Path(log).absolute()
    _require(batch == root / CANONICAL_SOURCE, "canonical source path differs")
    selected = [driver for driver in (HISTORICAL_DRIVER, NEW_DRIVER)
                if any(driver in shlex.split(command.replace("\\", "/"))
                       for command, _, _ in records)]
    if not selected:
        return None
    _require(len(selected) == 1, "one exact modern adaptation profile required")
    for path in (batch, log, root / selected[0], root / CODEX_CHECKER):
        _no_links(root, path)
        _regular(path)
    _require(log.parent == root / "smoketest_logs", "raw log must remain in smoketest_logs")
    from scripts.smoke_module import parse_smoke_module
    if selected[0] == HISTORICAL_DRIVER:
        _require(log == root / HISTORICAL_RAW and file_sha256(log) == HISTORICAL_RAW_SHA,
                 "historical raw identity mismatch")
        _require(file_sha256(root / HISTORICAL_DRIVER) == HISTORICAL_DRIVER_SHA,
                 "historical driver changed")
        receipt = root / HISTORICAL_RUNTIME / "isolation.json"
        data = _json_source(root, receipt)
        _require(file_sha256(receipt) == HISTORICAL_ISOLATION_SHA,
                 "historical pre-execution manifest changed")
        _require(data.get("source") == CANONICAL_SOURCE
                 and data.get("canonical_sha256") == file_sha256(batch)
                 and data.get("output_root") == str(root / HISTORICAL_RUNTIME)
                 and data.get("adaptations") == ["legacy_handoff_to_codex", "contract_reads_fresh_isolated_logs"],
                 "historical source/path/adaptation mismatch")
        recorded = data.get("action_manifest")
        _require(type(recorded) is list and bool(recorded), "historical action manifest missing")
        interpreter = _argv(recorded[0]["argv"])[0]
        canonical = _with_interpreter(parse_smoke_module(batch, log_name="smoke"), interpreter)
        adapted = []
        for action in canonical:
            argv = list(action.argv)
            if action.kind == "run" and "--" in argv:
                at = argv.index("--")
                if argv[at + 1:] == [interpreter, "scripts/check_handoff.py"]:
                    argv[at + 1:] = [interpreter, "-I", "-B", CODEX_CHECKER]
                elif argv[at + 1:] == [interpreter, "scripts/check_smoke.py"]:
                    argv[at + 1:] = [interpreter, "-B", "-X", "utf8", HISTORICAL_DRIVER,
                                    "--contract", "--root", str(root / HISTORICAL_RUNTIME)]
            adapted.append(replace(action, argv=tuple(argv)))
        _integer(data.get("canonical_actions"), len(canonical), "historical canonical count")
        _integer(data.get("actual_actions"), len(adapted), "historical actual count")
        _require(recorded == _manifest(adapted), "historical topology/argv manifest differs")
        summary = [interpreter, "-B", "-X", "utf8", "scripts/summarize_smoke.py"]
        return _validate_actual_blocks(log, records, adapted, interpreter, summary)

    contracts = []
    for command, _, _ in records:
        argv = shlex.split(command.replace("\\", "/"))
        if NEW_DRIVER in argv:
            at = argv.index(NEW_DRIVER)
            _require(argv[at + 1:at + 4] == ["--mode", "contract", "--session-id"]
                     and len(argv) == at + 5, "exact contract invocation required")
            contracts.append((argv[0], argv[-1]))
    _require(len(contracts) == 1, "one actual session contract required")
    interpreter, session_id = contracts[0]
    target = destinations(root, session_id)
    data = _json_source(root, target["report"])
    _require(data.get("schema") == NEW_SCHEMA and data.get("profile_id") == NEW_PROFILE_ID
             and data.get("session_id") == session_id, "unsupported normalized receipt identity")
    _require(data.get("source") == CANONICAL_SOURCE and data.get("driver") == NEW_DRIVER
             and data.get("runtime") == target["runtime"].relative_to(root).as_posix()
             and data.get("log_name") == target["log_name"]
             and data.get("raw_log_directory") == "smoketest_logs"
             and data.get("log") == log.relative_to(root).as_posix()
             and data.get("raw_logs") == [log.relative_to(root).as_posix()],
             "normalized source/runtime/raw identity mismatch")
    _require("_" + target["log_name"] + "_" in log.name, "session raw filename mismatch")
    _integer(data.get("log_bytes"), log.stat().st_size, "raw bytes")
    _require(log.stat().st_size < 20_000_000 and data.get("log_sha256") == file_sha256(log),
             "raw byte hash/size mismatch")
    pins = execution_source_pins(root)
    _require(data.get("source_pins_before") == pins == data.get("source_pins_after")
             and data.get("source_pins_unchanged") is True, "execution source pins differ")
    for name, path in (("source_sha256", CANONICAL_SOURCE), ("driver_sha256", NEW_DRIVER),
                       ("contract_module_sha256", CONTRACT_MODULE)):
        _require(data.get(name) == pins[path], name + " differs")
    canonical = _with_interpreter(parse_smoke_module(batch, log_name=target["log_name"]), interpreter)
    adapted, changes = adapt_actions(canonical, driver=NEW_DRIVER,
        contract_args=["--mode", "contract", "--session-id", session_id])
    _require(data.get("action_manifest") == _manifest(adapted)
             and data.get("substitutions") == changes, "canonical topology/argv/substitutions differ")
    children = [action for action in canonical if action.kind == "run" and "--" in action.argv]
    for name, expected in (("action_count", len(canonical)), ("child_count", len(children)),
                           ("training_count", sum("run100m.py" in action.argv for action in children)),
                           ("failed_calls", 0), ("failed_run_calls", 0), ("returncode", 0),
                           ("summary_returncode", 0)):
        _integer(data.get(name), expected, name)
    _require(data.get("complete") is True and data.get("summary_status") == "COMPLETE"
             and data.get("interrupted") is False and data.get("timed_out") is False
             and data.get("snapshot_errors") == [] and data.get("safety_errors") == [],
             "incomplete/unsafe normalized execution")
    moments = []
    for name in ("started_at", "finished_at", "deadline_utc"):
        value = data.get(name)
        _require(type(value) is str, "aware execution timestamps required")
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(moment.tzinfo is not None and moment.utcoffset() is not None,
                 "naive execution timestamp forbidden")
        moments.append(moment)
    _require(moments[0] <= moments[1] <= moments[2], "execution timestamps exceed deadline")
    _require(type(data.get("max_wall_sec")) in (int, float)
             and math.isfinite(data["max_wall_sec"]) and 0 < data["max_wall_sec"] <= 1800
             and type(data.get("whole_sec")) in (int, float)
             and math.isfinite(data["whole_sec"]) and 0 <= data["whole_sec"] <= data["max_wall_sec"],
             "invalid execution wall accounting")
    receipts = data.get("receipts")
    _require(type(receipts) is list and len(receipts) == len(canonical), "all action receipts required")
    for index, (original, actual, receipt) in enumerate(zip(canonical, adapted, receipts)):
        _require(type(receipt) is dict, "invalid action receipt")
        for name, expected in (("index", index), ("line", actual.line), ("seconds", actual.seconds),
                               ("returncode", 0)):
            _integer(receipt.get(name), expected, "receipt " + name)
        _require(receipt.get("kind") == actual.kind and receipt.get("status") == "COMPLETE"
                 and receipt.get("original_argv") == list(original.argv)
                 and receipt.get("executed_argv") == list(actual.argv)
                 and receipt.get("child") is (actual.kind == "run" and "--" in actual.argv)
                 and receipt.get("error") is None and not receipt.get("unsafe_process_state", False)
                 and type(receipt.get("duration_sec")) in (int, float)
                 and math.isfinite(receipt["duration_sec"]) and receipt["duration_sec"] >= 0,
                 "action state/argv/safety mismatch")
        if actual.kind == "run":
            _successful_process_state(receipt)
        else:
            _require(receipt.get("launch_state") in (None, "NOT_STARTED")
                     and receipt.get("process_started") in (None, False),
                     "sleep receipt contradicts no-child action")
            _require(receipt["duration_sec"] >= actual.seconds,
                     "completed canonical pause was shorter than declared")
    _require(data.get("original_synthetic_before_complete") is True
             and data.get("original_synthetic_after_complete") is True
             and data.get("original_synthetic_unchanged") is True,
             "synthetic preservation snapshot incomplete")
    before, after = data.get("original_synthetic_before"), data.get("original_synthetic_after")
    _snapshot_map(before)
    _snapshot_map(after)
    _require(before == after, "recorded synthetic bytes changed")
    # Never re-open original checkpoints or cache files here.
    env = data.get("environment")
    expected_env = dict(TINYLM_DIR=str(target["runtime"]), TINYLM_HF=str(target["runtime"] / "HF"),
        HF_HOME=str(target["runtime"] / "HF"), TL_OUTDIR="smoketest_logs", TL_LOGNAME=target["log_name"],
        TL_NOPAUSE="1", TL_WANDB_AUTO="0", WANDB_MODE="disabled", WANDB_DISABLED="true",
        HF_HUB_OFFLINE="1", HF_DATASETS_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    _require(type(env) is dict and all(type(key) is str and type(value) is str for key, value in env.items())
             and all(env.get(key) == value for key, value in expected_env.items()),
             "recorded isolated environment differs")
    # The writer owns its metadata allowlist. Read that literal, not the module
    # or any user environment, so no extra enum or executable import is needed.
    try:
        tree = ast.parse(_regular(root / NEW_DRIVER).read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise ValueError("invalid pinned driver source") from exc
    definitions = [node.value for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "ENVIRONMENT_KEYS"
                           for target in node.targets)]
    _require(len(definitions) == 1, "one literal source metadata allowlist required")
    try:
        allowed_env = ast.literal_eval(definitions[0])
    except (ValueError, TypeError, SyntaxError) as exc:
        raise ValueError("invalid source metadata allowlist") from exc
    _require(type(allowed_env) in (list, tuple) and all(type(key) is str for key in allowed_env)
             and set(env).issubset(allowed_env), "unexpected environment metadata key")
    _require(all(not any(word in key.upper() for word in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
                 for key in env), "secret-bearing environment metadata forbidden")
    summary = [interpreter, "scripts/summarize_smoke.py", "--log", str(log)]
    _require(data.get("summary_command") == [interpreter, "scripts/runlog.py", "--name",
             target["log_name"], "--", *summary], "summary wrapper argv differs")
    summary_receipt = data.get("summary_receipt")
    _require(type(summary_receipt) is dict and summary_receipt.get("status") == "COMPLETE"
             and summary_receipt.get("error") is None
             and summary_receipt.get("process_started") is True
             and not summary_receipt.get("unsafe_process_state", False), "unsafe/missing summary receipt")
    _integer(summary_receipt.get("returncode"), 0, "summary receipt exit")
    _successful_process_state(summary_receipt)
    _require(type(summary_receipt.get("duration_sec")) in (int, float)
             and math.isfinite(summary_receipt["duration_sec"])
             and summary_receipt["duration_sec"] >= 0, "invalid summary wall duration")
    serial_seconds = math.fsum([receipt["duration_sec"] for receipt in receipts]
                              + [summary_receipt["duration_sec"]])
    _require(data["whole_sec"] >= serial_seconds
             or math.isclose(data["whole_sec"], serial_seconds, rel_tol=1e-12, abs_tol=1e-12),
             "whole wall is shorter than sequential action receipts")
    return _validate_actual_blocks(log, records, adapted, interpreter, summary)
