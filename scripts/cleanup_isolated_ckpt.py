#!/usr/bin/env python3
"""격리 합성 스모크 체크포인트 정리. 기본은 읽기 전용이며 모델을 열지 않는다.

지원 범위는 runs/validation/codex_smoke/<session>/runs/ckpt 뿐이다.
성공 영수증/명령/원로그/결과 JSON으로 증명하지 못한 파일은 HOLD한다.
--interactive 또는 SHA로 고정한 --apply만 실제 파일을 지운다.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
TOOL_SOURCE = Path(__file__).resolve()
RUNTIME = Path("runs/validation/codex_smoke")
EVIDENCE = Path("test_result/evidence/codex_smoke")
AUDIT = Path("handoff/audit/isolated_checkpoint_cleanup")
SCHEMA = "TINYLM_ISOLATED_CKPT_CLEANUP_V1"
MAX_BYTES = 20_000_000
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
SAFE_NAME = re.compile(r"[A-Za-z0-9_]+")
SHA = re.compile(r"[0-9A-Fa-f]{64}")
REFERENCE_FIELDS = ("init_from_src", "kd_teacher")


class SafetyError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SafetyError(message)


def safe_path(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and relative.as_posix() == str(relative)
            and ".." not in relative.parts and "\\" not in str(relative),
            "정규화된 저장소 상대경로가 필요합니다")
    current = Path(root)
    for part in (None, *relative.parts):
        if part is not None:
            current /= part
        require(not current.is_symlink(), f"링크 경로는 보류합니다: {current}")
    return current


def identity(path):
    item = path.lstat()
    require(stat.S_ISREG(item.st_mode) and item.st_nlink == 1,
            f"일반 파일·단일 링크가 아닙니다: {path}")
    return dict(dev=item.st_dev, ino=item.st_ino, size=item.st_size,
                mtime_ns=item.st_mtime_ns, ctime_ns=item.st_ctime_ns,
                blocks_bytes=item.st_blocks * 512)


def read_file(root, relative, inputs):
    path = safe_path(root, relative)
    before = identity(path)
    require(before["size"] < MAX_BYTES, f"20MB 이상 메타데이터: {relative}")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
        opened = os.fstat(stream.fileno())
        require((opened.st_dev, opened.st_ino) == (before["dev"], before["ino"]), "읽기 중 교체")
        raw = stream.read(MAX_BYTES)
    require(identity(path) == before and len(raw) == before["size"], "읽기 중 변경")
    inputs[str(relative)] = dict(identity=before, sha256=hashlib.sha256(raw).hexdigest().upper())
    return raw


def read_json(root, relative, inputs):
    value = json.loads(read_file(root, relative, inputs).decode("utf-8"))
    require(type(value) is dict, f"JSON 객체가 아닙니다: {relative}")
    return value


def members(root, relative, directories):
    path = safe_path(root, relative)
    if not path.exists():
        directories[str(relative)] = None
        return []
    require(path.is_dir(), f"폴더가 아닙니다: {relative}")
    names = sorted(item.name for item in path.iterdir())
    directories[str(relative)] = names
    return names


def option(argv, name, default=None):
    require(argv.count(name) <= 1, f"중복 옵션: {name}")
    if name not in argv:
        return default
    at = argv.index(name) + 1
    require(at < len(argv) and not argv[at].startswith("--"), f"옵션 값 누락: {name}")
    return argv[at]


def training_stem(argv):
    """기록된 tiny synthetic train 명령만 해석한다. 명령을 실행하지 않는다."""
    require(argv[:3][1:] == ["run100m.py", "train"], "지원하지 않는 학습 명령")
    require("--tiny" in argv and option(argv, "--data") == "synthetic",
            "tiny synthetic만 정리할 수 있습니다")
    require(not any(x in argv for x in ("--m100", "--m30", "--preset", "--resume")),
            "다른 preset/재개 명령은 보류합니다")
    token = option(argv, "--tokens")
    require(type(token) is str and re.fullmatch(r"[1-9][0-9]*[KMG]?", token), "토큰 이름 계약 불명")
    count = int(token.rstrip("KMG")) * {"K": 1000, "M": 10**6, "G": 10**9}.get(token[-1], 1)
    token_name = f"{count // 10**6}M" if count >= 10**6 else str(count)
    arch = option(argv, "--arch")
    require(arch in ("dense", "tied"), "지원하지 않는 arch")
    tag = option(argv, "--tag", arch)
    require(SAFE_NAME.fullmatch(tag) is not None, "안전하지 않은 tag")
    return f"tiny_synthetic_{token_name}_{tag}", arch


def child_argv(action):
    argv = action.get("argv")
    require(action.get("kind") in ("run", "sleep") and type(argv) is list
            and all(type(x) is str for x in argv)
            and (bool(argv) or action["kind"] == "sleep"), "잘못된 argv")
    return argv[argv.index("--") + 1:] if action.get("kind") == "run" and "--" in argv else []


def successful_report(root, sid, inputs):
    runtime = RUNTIME / sid
    report = read_json(root, EVIDENCE / sid / "smoke_report.json", inputs)
    require(report.get("schema") == "TINYLM_CODEX_SMOKE_EXECUTION_V1"
            and report.get("profile_id") == "codex_isolated_smoke_v1"
            and report.get("session_id") == sid and report.get("runtime") == runtime.as_posix(),
            "지원하지 않는 영수증 또는 격리 경로 불일치")
    require(report.get("source") == "scripts/batch/tool_smoke.bat"
            and report.get("driver") == "scripts/codex_smoke.py", "실행 출처 불명")
    require(report.get("complete") is True and report.get("returncode") == 0
            and report.get("failed_calls") == 0 and report.get("failed_run_calls") == 0
            and report.get("summary_returncode") == 0 and report.get("summary_status") == "COMPLETE"
            and report.get("interrupted") is False and report.get("timed_out") is False
            and report.get("snapshot_errors") == [] and report.get("safety_errors") == [],
            "실패·중단·미완료 스모크는 자동 정리하지 않습니다")
    window = []
    for name in ("started_at", "finished_at"):
        moment = datetime.fromisoformat(report[name].replace("Z", "+00:00"))
        require(moment.tzinfo is not None and moment.utcoffset() is not None, "시각에 시간대가 없습니다")
        window.append(moment.timestamp())
    require(window[0] <= window[1], "실행 시작/종료 시각 역전")
    pins = report.get("source_pins_before")
    require(type(pins) is dict and bool(pins) and pins == report.get("source_pins_after")
            and report.get("source_pins_unchanged") is True
            and all(type(v) is str and SHA.fullmatch(v) for v in pins.values()), "실행 당시 소스 고정 실패")
    for field, name in (("source_sha256", report["source"]), ("driver_sha256", report["driver"]),
                        ("contract_module_sha256", "scripts/smoke_execution_contract.py")):
        require(report.get(field) == pins.get(name), "출처 SHA 불일치")
    # 옛 실행과 현재 코드의 SHA가 같아야 한다고 요구하지 않는다. 원본 파일은 열지 않는다.
    actions, receipts = report.get("action_manifest"), report.get("receipts")
    require(type(actions) is list and type(receipts) is list and actions
            and len(actions) == len(receipts) == report.get("action_count"), "행동 영수증 누락")
    children = []
    for index, (action, receipt) in enumerate(zip(actions, receipts)):
        child = child_argv(action)
        require(receipt.get("index") == index and receipt.get("line") == action.get("line")
                and receipt.get("kind") == action.get("kind")
                and receipt.get("executed_argv") == action["argv"]
                and receipt.get("child") is bool(child) and receipt.get("status") == "COMPLETE"
                and receipt.get("returncode") == 0 and receipt.get("error") is None
                and not receipt.get("unsafe_process_state", False)
                and not receipt.get("interrupted_during_cleanup", False), "행동 완료·안전 기록 불일치")
        if action["kind"] == "run":
            require(receipt.get("launch_state") == "OWNED" and receipt.get("process_started") is True,
                    "실제 실행 완료 근거 누락")
        else:
            require(not action["argv"] and not receipt.get("process_started", False)
                    and receipt.get("duration_sec", -1) >= action.get("seconds", 0), "대기 행동 불일치")
        if child:
            children.append(child)
    require(len(children) == report.get("child_count"), "child 수 불일치")
    log = report.get("log")
    require(type(log) is str and Path(log).parent == Path("smoketest_logs")
            and Path(log).suffix == ".txt", "원로그 경로 불명")
    raw = read_file(root, log, inputs)
    require(len(raw) == report.get("log_bytes")
            and inputs[log]["sha256"] == report.get("log_sha256"), "원로그 크기·SHA 불일치")
    text = raw.decode("utf-8")
    records = re.findall(r"^\[runlog\] cmd=(.*?)\n(.*?)^\[runlog\] 종료코드 (-?\d+)\s[^\n]*",
                         text, re.M | re.S)
    summary = child_argv(dict(kind="run", argv=report.get("summary_command")))
    require(len(records) == len(children) + 1
            and len(re.findall(r"^\[runlog\] cmd=", text, re.M)) == len(records), "원로그 블록 누락")
    for (command, _, code), expected in zip(records, children + [summary]):
        require(shlex.split(command) == expected and int(code) == 0, "원로그 명령·종료코드 불일치")
    trains = [child for child in children if "run100m.py" in child]
    require(len(trains) == report.get("training_count") and trains, "학습 기록 누락")
    stems = {}
    for child in trains:
        stem, arch = training_stem(child)
        require(stem not in stems, "동일 출력 중복 학습은 보류합니다")
        result = read_json(root, runtime / "runs/logs" / (stem + ".json"), inputs)
        require(result.get("preset") == "tiny" and result.get("data") == "synthetic"
                and result.get("arch") == arch and result.get("tag") == stem
                and type(result.get("final")) is dict, "학습 결과 출처 불일치")
        if "--steps" in child:
            require(result.get("steps") == int(option(child, "--steps")), "학습 step 불일치")
        stems[stem] = child
    return {stem + suffix for stem in stems for suffix in (".pt", "_best.pt")}, window


def reference_logs(root, sessions, inputs, directories):
    """기존 정리기와 같은 부모/교사 필드. 다른 폴더는 재귀 검색하지 않는다."""
    records = []
    for directory in [Path("runs/logs"), *(RUNTIME / sid / "runs/logs" for sid in sessions)]:
        for name in members(root, directory, directories):
            if name.endswith(".json"):
                path = directory / name
                data = read_json(root, path, inputs)
                for key in REFERENCE_FIELDS:
                    value = data.get(key)
                    if value:
                        require(type(value) is str, f"부모 참조 형식 불명: {path}")
                        records.append((str(path), value))
    return records


def busy_sessions(root, sessions, targets):
    """같은 UID의 격리 실행과 열린 후보 fd를 확인한다. 확인 불가는 fail closed."""
    require(sys.platform.startswith("linux") and Path("/proc/self/fd").is_dir(),
            "삭제 안전 검사는 Linux /proc가 필요합니다")
    active = set()
    inodes = {(v["dev"], v["ino"]): sid for sid, v in targets}
    paths = {sid: str(root / RUNTIME / sid) for sid in sessions}
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            env = (process / "environ").read_bytes().split(b"\0")
            command = (process / "cmdline").read_bytes().split(b"\0")
            for sid, path in paths.items():
                driver = any(Path(os.fsdecode(part)).name == "codex_smoke.py" for part in command)
                if (f"TINYLM_DIR={path}".encode() in env
                        or (driver and sid.encode() in command)):
                    active.add(sid)
            for fd in (process / "fd").iterdir():
                try:
                    item = fd.stat()
                except FileNotFoundError:
                    continue
                sid = inodes.get((item.st_dev, item.st_ino))
                if sid:
                    active.add(sid)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as exc:
            raise SafetyError("같은 UID 프로세스의 실행/열린 파일을 확인할 수 없습니다") from exc
    return active


def build_plan(root=ROOT, session_ids=None, *, busy_check=busy_sessions):
    root = Path(root).absolute()
    inputs, directories = {}, {}
    all_sessions = members(root, RUNTIME, directories)
    require(all(SAFE_ID.fullmatch(sid) for sid in all_sessions), "격리 세션 이름 불명")
    selected = sorted(set(session_ids if session_ids is not None else all_sessions))
    require(all(sid in all_sessions for sid in selected), "요청한 격리 세션이 없습니다")
    rows = []
    for sid in selected:
        row = dict(session_id=sid, status="ELIGIBLE", reason="완료 영수증·출처 일치", files=[])
        try:
            ckpt = RUNTIME / sid / "runs/ckpt"
            names = members(root, ckpt, directories)
            allowed, window = successful_report(root, sid, inputs)
            require(set(names) <= allowed, "영수증에 없는 파일·하위폴더가 있어 세션 전체 보류")
            for name in names:
                path = ckpt / name
                item = identity(safe_path(root, path))
                require(item["size"] > 0, "빈 체크포인트")
                require(window[0] <= item["mtime_ns"] / 10**9 <= window[1],
                        "체크포인트 수정시각이 기록된 실행 구간 밖입니다")
                parent = safe_path(root, ckpt).stat()
                row["files"].append(dict(path=path.as_posix(), identity=item,
                                         parent=dict(dev=parent.st_dev, ino=parent.st_ino)))
            if not names:
                row.update(status="EMPTY", reason="체크포인트 없음")
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
            row.update(status="HOLD", reason=str(exc), files=[])
        rows.append(row)
    try:
        refs = reference_logs(root, all_sessions, inputs, directories)
        registry = safe_path(root, "checkpoints.tsv")
        protected = set()
        if registry.exists():
            for line in read_file(root, "checkpoints.tsv", inputs).decode("utf-8").splitlines():
                cells = line.split("\t")
                if len(cells) > 1 and cells[0] in ("keep", "hold"):
                    protected.add(cells[1])
        targets = [(row["session_id"], item["identity"]) for row in rows for item in row["files"]]
        busy = busy_check(root, all_sessions, targets) if targets else set()
        for row in rows:
            if not row["files"]:
                continue
            sid = row["session_id"]
            names = {Path(item["path"]).name for item in row["files"]}
            base = {name.removesuffix("_best.pt").removesuffix(".pt") for name in names}
            family = {stem + suffix for stem in base for suffix in (".pt", "_best.pt")}
            reason = None
            if family & protected:
                reason = "checkpoints.tsv의 keep/hold와 이름이 겹칩니다"
            for origin, value in refs:
                name = Path(value.replace("\\", "/")).name
                if name not in family:
                    continue
                local = RUNTIME / sid / "runs"
                value_path = Path(value)
                origin_path = Path(origin)
                resolved = None
                clean = ".." not in value_path.parts and "\\" not in value
                if clean and value_path.is_absolute() and value_path.is_relative_to(root / RUNTIME):
                    resolved = safe_path(root, value_path.relative_to(root))
                elif clean and not value_path.is_absolute() and value_path.is_relative_to(RUNTIME):
                    resolved = safe_path(root, value_path)
                elif clean and origin_path.is_relative_to(RUNTIME):
                    owner = Path(*origin_path.parts[:len(RUNTIME.parts) + 1])
                    if len(value_path.parts) == 1 or value_path == Path("runs/ckpt") / name:
                        resolved = root / owner / "runs/ckpt" / name
                # 같은 이름이어도 참조한 격리폴더 안의 출력으로 경로를 해석한다.
                # root basename, 외부 경로, 상위 경로 등은 불명확하므로 같은 이름을 모두 보호한다.
                if resolved is not None and resolved != root / local / "ckpt" / name:
                    continue
                internal = origin_path.is_relative_to(local / "logs") and resolved is not None
                if not internal:
                    reason = f"다른 런의 부모/교사 참조: {origin}"
            if sid in busy:
                reason = "격리 실행 중이거나 후보 파일을 다른 프로세스가 열었습니다"
            if reason:
                row.update(status="HOLD", reason=reason, files=[])
    except (OSError, ValueError, TypeError) as exc:
        for row in rows:
            if row["files"]:
                row.update(status="HOLD", reason=f"보호 참조 확인 실패: {exc}", files=[])
    return dict(schema=SCHEMA, root=str(root), sessions=selected, rows=rows,
                inputs=inputs, directories=directories,
                tool_sha256=hashlib.sha256(TOOL_SOURCE.read_bytes()).hexdigest().upper())


def encoded(value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    require(len(raw) < MAX_BYTES, "감사 파일 20MB 상한 초과")
    return raw


def write_new(root, relative, value):
    relative = Path(relative)
    require(relative.is_relative_to(AUDIT) and relative.suffix == ".json", "감사 폴더의 새 JSON 경로 필요")
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = encoded(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest().upper()


def preview(plan):
    files = [item for row in plan["rows"] for item in row["files"]]
    print("격리 합성 스모크 체크포인트 — 삭제 전 정확한 후보 조회")
    for row in plan["rows"]:
        print(f"[{row['status']}] {row['session_id']}: {len(row['files'])}개 / {row['reason']}")
        for item in row["files"]:
            print(f"  {item['path']}  {item['identity']['size']:,} bytes")
    print(f"후보 {len(files)}개 / 논리 {sum(x['identity']['size'] for x in files):,} bytes"
          f" / 할당 {sum(x['identity']['blocks_bytes'] for x in files):,} bytes")
    print("원로그·결과 JSON·보고서·폴더·일반 체크포인트는 삭제 대상이 아닙니다.")


@contextmanager
def parent_fd(root, relative):
    """경로의 모든 폴더를 NOFOLLOW/openat으로 열고 unlink도 같은 fd에서 한다."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in Path(relative).parent.parts:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def delete_one(root, item):
    path = Path(item["path"])
    with parent_fd(root, path) as fd:
        parent = os.fstat(fd)
        require(dict(dev=parent.st_dev, ino=parent.st_ino) == item["parent"], "삭제 직전 부모 폴더 변경")
        # /proc/self/fd는 이미 검증한 폴더 fd를 통해 최종 파일만 lstat한다.
        require(identity(Path(f"/proc/self/fd/{fd}") / path.name) == item["identity"], "삭제 직전 파일 변경")
        os.unlink(path.name, dir_fd=fd)


def apply_plan(plan, root=ROOT, *, busy_check=busy_sessions, unlink=delete_one):
    root = Path(root).absolute()
    require(plan.get("schema") == SCHEMA and plan.get("root") == str(root), "다른 정리 계약/저장소")
    require(plan == build_plan(root, plan.get("sessions"), busy_check=busy_check), "조회 이후 목록·파일·참조가 변경됐습니다")
    files = [item for row in plan["rows"] for item in row["files"]]
    if not files:
        return dict(status="EMPTY", deleted=0, deleted_bytes=0)
    base = safe_path(root, AUDIT)
    base.mkdir(parents=True, exist_ok=True)
    lock = safe_path(root, AUDIT / ".cleanup.lock")
    with os.fdopen(os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600), "w") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # 잠금을 기다리는 동안 변한 증거도 거절한다.
        require(plan == build_plan(root, plan["sessions"], busy_check=busy_check), "잠금 직전 증거 변경")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12]
        folder = AUDIT / stamp
        write_new(root, folder / "plan.json", plan)
        free_before = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
        receipt = dict(schema=SCHEMA, status="PARTIAL_ERROR", expected=len(files), deleted=0,
                       deleted_bytes=0, error=None, audit=folder.as_posix(), free_before=free_before)
        journal = None
        try:
            journal_part, journal_bytes = 0, 0
            for item in files:
                for event in ("INTENT", "DELETED"):
                    if event == "DELETED":
                        unlink(root, item)
                        receipt["deleted"] += 1
                        receipt["deleted_bytes"] += item["identity"]["size"]
                    line = (json.dumps(dict(event=event, **item), ensure_ascii=False) + "\n").encode("utf-8")
                    if journal is None or journal_bytes + len(line) >= MAX_BYTES:
                        if journal is not None:
                            journal.close()
                        journal_part += 1
                        journal = safe_path(root, folder / f"journal_{journal_part:04}.jsonl").open("xb")
                        journal_bytes = 0
                    journal.write(line)
                    journal.flush()
                    os.fsync(journal.fileno())
                    journal_bytes += len(line)
            receipt["status"] = "COMPLETE"
        except BaseException as exc:
            receipt["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            if journal is not None:
                journal.close()
            receipt["free_after"] = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize
            receipt["free_delta"] = receipt["free_after"] - free_before
            write_new(root, folder / "receipt.json", receipt)
            print(f"감사 영수증: {folder / 'receipt.json'} / {receipt['status']} / 실제 삭제 {receipt['deleted']}개")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", action="store_true", help="조회한 목록을 YES로 확인한 뒤 삭제")
    mode.add_argument("--apply", action="store_true", help="사용자가 승인한 manifest와 SHA로만 삭제")
    parser.add_argument("--session-id", action="append", help="정확한 격리 세션만 조회; 반복 지정 가능")
    parser.add_argument("--output", help="조회 목록을 감사 폴더의 새 JSON으로 보존")
    parser.add_argument("--manifest", help="--apply에서 사용할 기존 조회 목록")
    parser.add_argument("--manifest-sha256", help="검토·승인한 조회 목록의 SHA-256")
    args = parser.parse_args(argv)
    try:
        require(not (args.apply and (args.output or args.session_id)), "apply에서 후보를 바꾸지 마세요")
        require(args.apply or not (args.manifest or args.manifest_sha256), "manifest는 apply 전용입니다")
        if args.apply:
            require(args.manifest and args.manifest_sha256 and SHA.fullmatch(args.manifest_sha256),
                    "--apply는 --manifest 및 --manifest-sha256이 모두 필요합니다")
            relative = Path(args.manifest)
            require(relative.is_relative_to(AUDIT), "정리 감사 폴더의 manifest만 허용합니다")
            raw = read_file(ROOT, relative, {})
            require(hashlib.sha256(raw).hexdigest().upper() == args.manifest_sha256.upper(), "manifest SHA 불일치")
            plan = json.loads(raw)
        else:
            plan = build_plan(ROOT, args.session_id)
        preview(plan)
        if args.output:
            print("목록 SHA-256:", write_new(ROOT, args.output, plan))
        if args.apply:
            apply_plan(plan, ROOT)
        elif args.interactive and any(row["files"] for row in plan["rows"]):
            print("해당 파일만 영구 삭제합니다. 관련 실행을 먼저 종료하세요.")
            if input("계속하려면 대문자 YES 입력: ").strip() != "YES":
                print("취소: 삭제하지 않았습니다.")
                return 0
            apply_plan(plan, ROOT)
        else:
            print("조회 완료: 실제 삭제하지 않았습니다.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        print(f"[STOP] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
