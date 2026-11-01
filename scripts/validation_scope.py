"""Explicit, opt-in inputs for Python static validators.

No environment setting means USER_GLOBAL. OWN_SCOPED runs the original checker
in a separate process with a manifest-backed directory view and an audited read
boundary. This is a Python validation harness, not an OS security sandbox.
Opaque/native child commands are rejected rather than reported as observed.
"""
from __future__ import annotations

import fnmatch
import hashlib
import importlib.machinery
import io
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = "TL_VALIDATION_SCOPE"
ENV_SHA = "TL_VALIDATION_SCOPE_SHA256"
SCHEMA = "TINYLM_VALIDATION_SCOPE_V1"
RECEIPT_SCHEMA = "TINYLM_VALIDATION_SCOPE_RECEIPT_V1"
MODE = "OWN_SCOPED"
BOOTSTRAP = "scripts/validation_scope.py"
FORBIDDEN = (
    "datasets/TinyDataset", ".claude", "CLAUDE.md", "ai_dev_tool/00",
    "ai_dev_tool/01", "ai_dev_tool/02", "ai_dev_tool/03", "ai_dev_tool/04",
    "ai_dev_tool/05", "ai_dev_tool/06", "ai_dev_tool/07", "ai_dev_tool/08",
)
_ACTIVE = None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def _relative(value):
    if type(value) is not str or not value or "\\" in value:
        raise ValueError("one explicit POSIX relative file path required")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ValueError("canonical repository relative path required")
    for forbidden in FORBIDDEN:
        if value == forbidden or value.startswith(forbidden + "/") or (
                forbidden.startswith("ai_dev_tool/") and value.startswith(forbidden)):
            raise ValueError("protected or foreign-exclusive scope input")
    return value


def _regular(root, name):
    path = root / _relative(name)
    cursor = root
    for part in PurePosixPath(name).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("linked scope inputs are forbidden")
    if not path.is_file():
        raise ValueError("scope input must be an existing regular file: " + name)
    if path.stat().st_nlink != 1:
        raise ValueError("hardlinked scope inputs are forbidden")
    return path


def _target_key(target, root=ROOT):
    values = list(target)
    if not values or any(type(x) is not str for x in values):
        raise ValueError("explicit Python target argv required")
    if values[0] not in ("-c", "-m"):
        candidate = Path(values[0])
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            values[0] = candidate.absolute().relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError("Python script must be inside scope repository") from exc
        _relative(values[0])
    return values


class Scope:
    def __init__(self, path, expected_sha, *, root=ROOT):
        self.root = Path(root).resolve()
        path = Path(path).absolute()
        try:
            name = path.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError("scope manifest must be inside repository") from exc
        self.path = _regular(self.root, name)
        if type(expected_sha) is not str or len(expected_sha) != 64:
            raise ValueError("explicit manifest SHA-256 required")
        self.digest = sha256(self.path)
        if self.digest != expected_sha.upper():
            raise ValueError("scope manifest SHA mismatch")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA or data.get("mode") != MODE:
            raise ValueError("explicit OWN_SCOPED schema required")
        if data.get("repository") != str(self.root):
            raise ValueError("scope repository identity mismatch")
        if not isinstance(data.get("exclusions"), list) or not data["exclusions"]:
            raise ValueError("scope exclusions must be recorded")
        self.exclusions = data["exclusions"]
        if any(type(x) is not str or not x or PurePosixPath(x).is_absolute()
               or ".." in PurePosixPath(x).parts or "\\" in x
               for x in self.exclusions):
            raise ValueError("explicit excluded repository prefixes required")
        self.data = data
        self.inputs = {}
        for entry in data.get("inputs", []):
            name = _relative(entry["path"])
            if any(name == x or name.startswith(x.rstrip("/") + "/")
                   or (x.endswith("*") and name.startswith(x[:-1])) for x in self.exclusions):
                raise ValueError("input overlaps an explicitly excluded prefix")
            if name in self.inputs or entry.get("role") not in ("owned", "shared"):
                raise ValueError("duplicate input or unknown ownership role")
            path = _regular(self.root, name)
            if entry.get("sha256") != sha256(path):
                raise ValueError("scope input SHA mismatch: " + name)
            self.inputs[name] = dict(entry)
        if BOOTSTRAP not in self.inputs:
            raise ValueError("scope bootstrap must be pinned as a shared input")
        if not self.inputs:
            raise ValueError("nonempty explicit inputs required")
        self.commands = {}
        for entry in data.get("commands", []):
            name, argv = entry["name"], entry["argv"]
            if type(name) is not str or name in self.commands:
                raise ValueError("unique named scope commands required")
            key = _target_key(argv, self.root)
            if key != argv or key[0] not in self.inputs:
                raise ValueError("scope command must name a pinned script")
            self.commands[name] = key
        if not self.commands:
            raise ValueError("at least one named scope command required")
        self.child_commands = data.get("child_commands", [])
        if (type(self.child_commands) is not list
                or any(type(x) is not list or _target_key(x, self.root) != x
                       for x in self.child_commands)):
            raise ValueError("exact child target argv list required")

    def unchanged(self):
        return (sha256(self.path) == self.digest and all(
            sha256(_regular(self.root, name)) == row["sha256"]
            for name, row in self.inputs.items()))

    def evidence(self):
        return dict(mode=MODE, manifest=self.path.relative_to(self.root).as_posix(),
                    manifest_sha256=self.digest, input_count=len(self.inputs),
                    inputs=list(self.inputs.values()), exclusions=self.data["exclusions"],
                    global_pass_eligible=False, collector="explicit-input-view-v1",
                    guard="Python audit; native children forbidden; not an OS sandbox")

    def output_path(self, value):
        path = Path(value).absolute()
        try:
            name = path.relative_to(self.root).as_posix()
        except ValueError as exc:
            raise ValueError("scope output must remain inside repository") from exc
        _relative(name)
        if any(name == x or name.startswith(x.rstrip("/") + "/")
               or (x.endswith("*") and name.startswith(x[:-1])) for x in self.exclusions):
            raise ValueError("scope output overlaps an excluded prefix")
        cursor = self.root
        for part in PurePosixPath(name).parts:
            cursor /= part
            if cursor.is_symlink():
                raise ValueError("linked scope output forbidden")
        return path


def from_environment(env=None):
    env = os.environ if env is None else env
    path, digest = env.get(ENV_PATH), env.get(ENV_SHA)
    if not path and not digest:
        return None
    if not path or not digest:
        raise ValueError("scope path and SHA must be provided together")
    return Scope(path, digest)


def _python_target(command):
    if type(command) not in (list, tuple) or not command:
        raise ValueError("explicit Python argv list required")
    interpreter = str(command[0])
    if (not Path(interpreter).name.startswith(("python", "pypy"))
            or Path(interpreter).resolve() != Path(sys.executable).resolve()):
        raise ValueError("opaque/native child is not supported by scoped validation")
    flags, i = [], 1
    while i < len(command):
        item = str(command[i])
        if item in ("-c", "-m") or not item.startswith("-"):
            break
        if item in ("-X", "-W"):
            if i + 1 >= len(command):
                raise ValueError("incomplete Python interpreter option")
            flags.extend((item, str(command[i + 1])))
            i += 2
        elif item in ("-I", "-B", "-E", "-s", "-S", "-u", "-O", "-OO", "-q"):
            flags.append(item)
            i += 1
        else:
            raise ValueError("unsupported Python interpreter option: " + item)
    target = [str(x) for x in command[i:]]
    if not target or target[0] == "-":
        raise ValueError("stdin/empty Python targets are not supported")
    return interpreter, flags, target


def scoped_command(command, scope, receipt, name):
    interpreter, flags, target = _python_target(command)
    key = _target_key(target, scope.root)
    if name == "__child__":
        if key not in scope.child_commands:
            raise ValueError("child target is absent from explicit child commands")
    elif scope.commands.get(name) != key:
        raise ValueError("scope command does not match canonical target argv")
    return [interpreter, *flags, str(scope.root / BOOTSTRAP), "worker",
            str(scope.path), scope.digest, str(receipt), name, "--", *target]


def rows_for_selected_sources(rows, parser_flags=None):
    """Choose table inputs before the original bidirectional predicates run."""
    if _ACTIVE is None:
        return rows
    selected = set(_ACTIVE.scope.inputs)
    # Grades are global per flag. declared_in is historical metadata, not the
    # parser-owned flag inventory; a selected parser may legitimately reuse it.
    flags = set(parser_flags()) if parser_flags is not None else set()
    return {flag: row for flag, row in rows.items()
            if flag in flags or any(name.strip() in selected for name in row[3].split(","))}


def _matches(parts, pattern):
    if not pattern:
        return not parts
    if pattern[0] == "**":
        return _matches(parts, pattern[1:]) or bool(parts) and _matches(parts[1:], pattern)
    return bool(parts) and fnmatch.fnmatchcase(parts[0], pattern[0]) and _matches(parts[1:], pattern[1:])


class Boundary:
    def __init__(self, scope, receipt):
        self.scope = scope
        self.root = scope.root
        self.receipt = scope.output_path(receipt)
        self.out = self.receipt.parent
        if self.root not in self.out.parents or self.out == self.root:
            raise ValueError("scope receipt requires a separate repository output directory")
        _relative(self.out.relative_to(self.root).as_posix())
        for parent in (self.out, *self.out.parents):
            if parent == self.root.parent:
                break
            if parent.is_symlink():
                raise ValueError("linked receipt directory forbidden")
        if self.receipt.exists():
            raise ValueError("scope receipts are write-once")
        self.out.mkdir(parents=True, exist_ok=True)
        self.reads, self.denials, self.children = set(), [], []
        self.permitted_spawn = 0
        self.original_popen = subprocess.Popen
        self.entries = set(scope.inputs)
        self.entries.add(scope.path.relative_to(self.root).as_posix())
        for name in list(self.entries):
            self.entries.update(p.as_posix() for p in PurePosixPath(name).parents
                                if p.as_posix() != ".")

    def repo_name(self, raw):
        if isinstance(raw, int):
            return None
        try:
            path = os.fsdecode(raw)
        except TypeError:
            return None
        absolute = Path(os.path.abspath(path))
        resolved = Path(os.path.realpath(absolute))
        if self.root in absolute.parents or absolute == self.root:
            if resolved != absolute:
                self.deny("linked repository access", str(absolute))
            return absolute.relative_to(self.root).as_posix()
        if self.root in resolved.parents or resolved == self.root:
            self.deny("repository alias access", str(absolute))
        return None

    def deny(self, reason, raw):
        self.denials.append(dict(reason=reason,
                                 attempted_path_sha256=hashlib.sha256(str(raw).encode()).hexdigest().upper()))
        raise PermissionError("OWN_SCOPED boundary: " + reason)

    def audit(self, event, args):
        if event == "open":
            raw, mode, flags = args
            name = self.repo_name(raw)
            if name is None:
                return
            path = self.root / name
            output = path == self.out or self.out in path.parents
            writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing:
                if not output:
                    self.deny("repository write outside receipt directory", name)
            elif not output:
                if name not in self.scope.inputs and path != self.scope.path:
                    self.deny("unlisted repository read", name)
                self.reads.add(name)
        elif event == "subprocess.Popen":
            if not self.permitted_spawn:
                self.deny("unwrapped subprocess", args[0])
        elif event in ("os.listdir", "os.scandir"):
            if self.repo_name(args[0]) is not None:
                self.deny("directory enumeration outside explicit collector view", event)
        elif event == "os.chdir":
            if isinstance(args[0], int) or Path(args[0]).absolute() != self.root:
                self.deny("scope working directory change", args[0])
        elif event in ("os.system", "os.exec", "os.fork", "os.forkpty", "os.posix_spawn"):
            if not self.permitted_spawn:
                self.deny("unobserved process execution", event)
        elif event in ("os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.link", "os.symlink"):
            paths = args[:2] if event in ("os.rename", "os.link", "os.symlink") else args[:1]
            for raw in paths:
                name = self.repo_name(raw)
                if name is not None and not (self.root / name == self.out or self.out in (self.root / name).parents):
                    self.deny("repository mutation outside receipt directory", name)
        elif event == "import" and args[0] in ("ctypes", "_ctypes"):
            self.deny("unobserved native FFI import", args[0])

    def paths(self, base, pattern="*", recursive=False):
        name = self.repo_name(base)
        if name is None:
            return None
        prefix = () if name == "." else PurePosixPath(name).parts
        pattern = PurePosixPath(pattern).parts
        if recursive:
            pattern = ("**", *pattern)
        result = []
        for candidate in self.entries:
            parts = PurePosixPath(candidate).parts
            if parts[:len(prefix)] == prefix and len(parts) > len(prefix):
                if _matches(parts[len(prefix):], pattern):
                    result.append(self.root / candidate)
        return sorted(result)

    def popen(self, command, *args, **kwargs):
        try:
            if kwargs.get("shell") or kwargs.get("executable"):
                raise ValueError("shell/executable override is unsupported")
            if kwargs.get("cwd") is not None and Path(kwargs["cwd"]).absolute() != self.root:
                raise ValueError("scoped child cwd must remain repository root")
            receipt = self.out / (self.receipt.stem + ".child" + str(len(self.children)) + ".json")
            wrapped = scoped_command(command, self.scope, receipt, "__child__")
        except (ValueError, TypeError) as exc:
            self.deny(str(exc), command)
        env = dict(os.environ if kwargs.get("env") is None else kwargs["env"])
        env[ENV_PATH], env[ENV_SHA] = str(self.scope.path), self.scope.digest
        kwargs["env"] = env
        self.permitted_spawn += 1
        try:
            process = self.original_popen(wrapped, *args, **kwargs)
        finally:
            self.permitted_spawn -= 1
        self.children.append((process, receipt))
        return process

    def install(self):
        global _ACTIVE
        _ACTIVE = self
        sys.addaudithook(self.audit)
        original_glob, original_rglob, original_iterdir = Path.glob, Path.rglob, Path.iterdir
        def view_glob(path, pattern, **kwargs):
            found = self.paths(path, pattern)
            return original_glob(path, pattern, **kwargs) if found is None else iter(found)
        def view_rglob(path, pattern, **kwargs):
            found = self.paths(path, pattern, True)
            return original_rglob(path, pattern, **kwargs) if found is None else iter(found)
        def view_iterdir(path):
            found = self.paths(path)
            return original_iterdir(path) if found is None else iter(found)
        Path.glob, Path.rglob, Path.iterdir = view_glob, view_rglob, view_iterdir
        original_listdir, original_scandir = os.listdir, os.scandir
        def view_listdir(path="."):
            found = self.paths(path)
            return original_listdir(path) if found is None else [x.name for x in found]
        class Entry:
            def __init__(self, path):
                self.path, self.name = str(path), path.name
            def __fspath__(self):
                return self.path
            def is_dir(self, *, follow_symlinks=True):
                return Path(self.path).is_dir()
            def is_file(self, *, follow_symlinks=True):
                return Path(self.path).is_file()
            def is_symlink(self):
                return False
            def stat(self, *, follow_symlinks=True):
                return os.stat(self.path, follow_symlinks=follow_symlinks)
        class Entries:
            def __init__(self, paths):
                self.iterator = iter(Entry(path) for path in paths)
            def __iter__(self):
                return self
            def __next__(self):
                return next(self.iterator)
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                self.close()
            def close(self):
                pass
        def view_scandir(path="."):
            found = self.paths(path)
            return original_scandir(path) if found is None else Entries(found)
        os.listdir, os.scandir = view_listdir, view_scandir
        subprocess.Popen = self.popen
        original_code = importlib.machinery.SourceFileLoader.get_code
        def source_only(loader, fullname):
            filename = loader.get_filename(fullname)
            if self.repo_name(filename) is None:
                return original_code(loader, fullname)
            return loader.source_to_code(loader.get_data(filename), filename)
        importlib.machinery.SourceFileLoader.get_code = source_only

    def finish(self, name, target, code):
        checker_reads = sorted(self.reads)
        child_rows = []
        for process, receipt in self.children:
            if process.poll() is None:
                self.denials.append(dict(reason="child still running at parent return"))
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if not receipt.is_file():
                self.denials.append(dict(reason="child receipt missing"))
                continue
            row = json.loads(receipt.read_text(encoding="utf-8"))
            if (row.get("schema") != RECEIPT_SCHEMA or row.get("mode") != MODE
                    or row.get("manifest_sha256") != self.scope.digest
                    or row.get("inputs_unchanged") is not True
                    or row.get("actual_returncode") != process.returncode
                    or row.get("scope_violations")):
                self.denials.append(dict(reason="child boundary failed"))
            child_rows.append(dict(receipt=receipt.relative_to(self.root).as_posix(),
                                   returncode=process.returncode,
                                   receipt_sha256=sha256(receipt),
                                   scope_violations=row.get("scope_violations")))
        unchanged = self.scope.unchanged()
        if not unchanged:
            self.denials.append(dict(reason="input or manifest changed during validation"))
        result = dict(schema=RECEIPT_SCHEMA, **self.scope.evidence(), command=name,
                      target_argv=_target_key(target, self.root), checker_returncode=code,
                      checker_reads=checker_reads, actual_reads=sorted(self.reads),
                      integrity_reads=list(self.scope.inputs), children=child_rows,
                      scope_violations=self.denials, inputs_unchanged=unchanged,
                      actual_returncode=91 if self.denials else code,
                      external_reads="Python/runtime outside repository not inventoried")
        payload = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(payload) >= 20_000_000:
            raise ValueError("scope receipt exceeds result-file size limit")
        with self.receipt.open("xb") as stream:
            stream.write(payload)
        return result["actual_returncode"]


def _worker(argv):
    manifest, digest, receipt, name, separator, *target = argv
    if separator != "--":
        raise ValueError("worker requires an explicit target separator")
    scope = Scope(manifest, digest)
    if name == "__child__":
        if _target_key(target) not in scope.child_commands:
            raise ValueError("unregistered child target")
    elif scope.commands.get(name) != _target_key(target):
        raise ValueError("unregistered checker target")
    boundary = Boundary(scope, receipt)
    boundary.install()
    code = 0
    # The bootstrap alias lets checkers consult the active collector without a
    # second module instance. Preserve -I: do not add the target directory there.
    sys.modules["validation_scope"] = sys.modules[__name__]
    if not sys.flags.isolated:
        sys.path[0] = str(Path(target[0]).absolute().parent) if target[0] not in ("-c", "-m") else str(Path.cwd())
    try:
        sys.argv = list(target)
        if target[0] == "-c":
            sys.argv = ["-c", *target[2:]]
            exec(compile(target[1], "<scoped-child>", "exec"), {"__name__": "__main__", "__builtins__": __builtins__})
        elif target[0] == "-m":
            sys.argv = target[1:]
            runpy.run_module(target[1], run_name="__main__", alter_sys=True)
        else:
            runpy.run_path(target[0], run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        if exc.code is not None and not isinstance(exc.code, int):
            print(exc.code, file=sys.stderr)
    except BaseException:
        traceback.print_exc()
        code = 1
    return boundary.finish(name, target, code)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "worker":
        raise SystemExit("Use the opt-in scope environment through check_static_all.py")
    try:
        raise SystemExit(_worker(sys.argv[2:]))
    except (ValueError, OSError) as error:
        print("OWN_SCOPED ERROR:", error, file=sys.stderr)
        raise SystemExit(91)
