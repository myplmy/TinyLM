"""고정 IQ2 worker의 날짜 한정 파생 빌드와 소유 프로세스 감독."""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OLD_EPOCH = 1792798800
NEW_EPOCH = 1792900800
FOLDER = "worker_window_20261025_v1"
WORKER = FOLDER + "/worker_window_001"
OWNER_KEY = "TINYLM_IQ2_WINDOW_OWNER"
MAX_BYTES = 20_000_000
SCHEMA = "P106B_IQ2_WORKER_WINDOW_20261025_V1"
SUPERVISOR_RESERVE = 60
MAX_PARENT_CAP = 17400
OLD_TEXT = "deadline exceeds authorized 08:40 KST window"
NEW_TEXT = "deadline exceeds authorized 13:00 KST 25Oct window"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest().upper()


def regular(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and not any(p.is_symlink() for p in path.parents),
        "일반 파일과 실제 경로가 필요합니다: " + str(path))
    require(path.stat().st_size < MAX_BYTES, "파일의 20MB 상한을 넘었습니다")
    return path


def read_json(path):
    return json.loads(regular(path).read_text(encoding="utf-8"))


def write_once(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    require(len(raw) < MAX_BYTES, "보고서의 20MB 상한을 넘었습니다")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def derive_source(source):
    """두 리터럴 이외의 모든 바이트와 모델 입장 순서를 보존한다."""
    old = str(OLD_EPOCH).encode()
    require(source.count(old) == 1 and source.count(OLD_TEXT.encode()) == 1,
        "원 날짜 경계가 정확히 한 번 존재해야 합니다")
    guard = source.index(old)
    require(source.index(b'if(argc!=5') < guard < source.index(b'Runtime runtime(argv[2],architecture)'),
        "날짜와 미등록 경로 검사가 backend 초기화보다 앞서야 합니다")
    require(source.index(b'if(argv[2]!=allowed)') < source.index(b'Runtime runtime(argv[2],architecture)'),
        "모델 없는 경계 검사 순서가 바뀌었습니다")
    return source.replace(old, str(NEW_EPOCH).encode()).replace(OLD_TEXT.encode(), NEW_TEXT.encode())


def original_identity():
    from scripts import p106b_native_core6 as native
    frozen = native.identity()
    require(frozen["sha256"] == "42713A9E7A181896DAD0A10D0359BFA193264D9DAEF3445A05E970404995D2AD",
        "고정 평가기 신원이 다릅니다")
    return native, frozen


def build_identity(frozen=None):
    native, actual = original_identity()
    require(frozen is None or frozen == actual, "원 평가기 신원이 바뀌었습니다")
    directory = native.HEADERS / FOLDER
    if not directory.exists():
        return dict(status="NOT_READY", schema=SCHEMA, worker=WORKER, models=0, backend_initializations=0)
    require(not directory.is_symlink(), "파생 빌드 경로가 심볼릭 링크입니다")
    receipt = read_json(directory / "build_receipt.json")
    source = regular(ROOT / "scripts/p106b_native_llama_worker.cpp").read_bytes()
    derived = derive_source(source)
    require(receipt.get("schema") == SCHEMA and receipt.get("deadline_epoch") == NEW_EPOCH
        and receipt.get("original_native_sha256") == actual["sha256"]
        and receipt.get("original_build") == actual["build"] and receipt.get("worker") == WORKER,
        "파생 빌드 영수증의 원천 또는 날짜가 다릅니다")
    require(regular(directory / "worker_window.cpp").read_bytes() == derived,
        "파생 소스가 허용된 두 리터럴 이외를 바꿨습니다")
    require(digest(directory / "worker_window.cpp") == receipt["cpp_sha256"]
        and digest(native.HEADERS / WORKER) == receipt["worker_sha256"], "파생 빌드 해시가 다릅니다")
    require(receipt.get("cpu_probe_passed") is True and receipt.get("models") == 0
        and receipt.get("backend_initializations") == 0, "모델 없는 경계 검사가 완료되지 않았습니다")
    build = dict(actual["build"], worker=WORKER, worker_sha256=receipt["worker_sha256"],
        cpp_sha256=receipt["cpp_sha256"], worker_bytes=(native.HEADERS / WORKER).stat().st_size)
    return dict(status="READY", schema=SCHEMA, worker=WORKER, build=build,
        receipt_sha256=digest(directory / "build_receipt.json"), original_native_sha256=actual["sha256"],
        deadline_epoch=NEW_EPOCH, models=0, backend_initializations=0)


def cpu_probes(original, derived, *, runner=subprocess.run):
    """검사 경로는 원천에서 backend 이전 종료임을 확인한 뒤에만 호출한다."""
    path = "/__tinylm_unregistered_iq2_window_probe__"
    probes = []
    env = dict(os.environ, LD_LIBRARY_PATH="/home/uranus/llama-b11396")
    for name, argv, code, marker in (
        ("original_selftest", [str(original), "--self-test"], 0, "CPU_ONLY; backend_init=0; model_loads=0"),
        ("derived_selftest", [str(derived), "--self-test"], 0, "CPU_ONLY; backend_init=0; model_loads=0"),
        ("old_window_rejects_new", [str(original), "--execute", path, "qwen35", str(NEW_EPOCH - 1)], 9, OLD_TEXT),
        ("new_window_rejects_overrun", [str(derived), "--execute", path, "qwen35", str(NEW_EPOCH + 1)], 9, NEW_TEXT),
        ("new_window_reaches_path_guard", [str(derived), "--execute", path, "qwen35", str(NEW_EPOCH - 1)], 9,
            "unregistered model path; no backend initialized")):
        result = runner(argv, capture_output=True, text=True, timeout=20, check=False, env=env)
        require(result.returncode == code and marker in result.stdout + result.stderr,
            "모델 없는 경계 검사가 예상과 다릅니다: " + name)
        probes.append(dict(name=name, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    return probes


def prepare():
    native, frozen = original_identity()
    source_path = regular(ROOT / "scripts/p106b_native_llama_worker.cpp")
    source = source_path.read_bytes()
    derived = derive_source(source)
    directory = native.HEADERS / FOLDER
    require(not directory.exists() and not directory.is_symlink(), "기존 파생 빌드와 부분 결과를 보존합니다")
    before = {name: digest(ROOT / name) for name in frozen["files"]}
    directory.mkdir(exist_ok=False)
    cpp, binary = directory / "worker_window.cpp", native.HEADERS / WORKER
    with cpp.open("xb") as stream:
        stream.write(derived)
    build = frozen["build"]
    command = [build["compiler_resolved_path"], *build["compile_flags"],
        "-I" + str(native.HEADERS / "include"), "-I" + str(native.HEADERS / "ggml/include"),
        str(cpp), *build["link_flags"], "-o", str(binary)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    require(compiled.returncode == 0, "독립 CPU 컴파일 실패: " + compiled.stderr[:4000])
    probes = cpu_probes(native.HEADERS / build["worker"], binary)
    require(before == {name: digest(ROOT / name) for name in before} and native.identity() == frozen,
        "원 소스·worker·헤더·라이브러리가 바뀌었습니다")
    receipt = dict(schema=SCHEMA, worker=WORKER, deadline_epoch=NEW_EPOCH, original_native_sha256=frozen["sha256"],
        original_build=build, original_files=before, cpp_sha256=digest(cpp), worker_sha256=digest(binary),
        command=command, compiler_returncode=compiled.returncode, compiler_stdout=compiled.stdout,
        compiler_stderr=compiled.stderr, cpu_probes=probes, cpu_probe_passed=True,
        models=0, backend_initializations=0, original_files_unchanged=True,
        change_scope="DATE_LITERAL_AND_ITS_MESSAGE_ONLY")
    write_once(directory / "build_receipt.json", receipt)
    return build_identity(frozen)


def proc_stat(pid):
    raw = (Path("/proc") / str(pid) / "stat").read_text()
    fields = raw[raw.rfind(")") + 2:].split()
    return dict(pid=int(pid), state=fields[0], ppid=int(fields[1]), pgid=int(fields[2]),
        session=int(fields[3]), starttime=int(fields[19]))


def find_owned_workers(binary, token, controller, known=None):
    """정확한 실행파일을 먼저 찾은 경우에만 환경에서 소유 token을 읽는다."""
    binary = str(Path(binary).resolve(strict=True)); found = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        matched = False
        try:
            if os.readlink(entry / "exe") != binary:
                continue
            matched = True
            row = proc_stat(int(entry.name))
            if row["starttime"] < controller["starttime"]:
                continue
            environment = (entry / "environ").read_bytes()
            if (OWNER_KEY + "=" + token).encode() not in environment.split(b"\0"):
                continue
            old = (known or {}).get(row["pid"])
            require(old is None or old["starttime"] == row["starttime"], "관측한 worker PID가 재사용되었습니다")
            require(row["ppid"] in (controller["pid"], os.getpid()) or
                (old is not None and old["starttime"] == row["starttime"]), "worker 부모 소유 관계가 다릅니다")
            require(row["pid"] == row["pgid"] == row["session"] and row["pid"] > 1
                and row["pgid"] != os.getpgrp(), "worker의 독립 프로세스 그룹이 다릅니다")
            found[row["pid"]] = row
        except PermissionError:
            if matched:
                raise ValueError("정확 worker의 소유 환경을 읽지 못했습니다")
            continue
        except (FileNotFoundError, ProcessLookupError):
            continue
    return found


def set_subreaper(value):
    libc = ctypes.CDLL(None, use_errno=True)
    old = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(old), 0, 0, 0) != 0 or libc.prctl(36, int(value), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "고아 worker 회수 권한을 설정하지 못했습니다")
    return old.value


def append_veto(directory, value):
    for index in range(10000):
        path = Path(directory) / ("supervisor_veto_%05d.json" % index)
        try:
            write_once(path, value)
            return str(path)
        except FileExistsError:
            continue
    raise ValueError("감독 거부 기록 수 상한을 넘었습니다")


def cleanup_workers(binary, token, controller, known, expires):
    rows = find_owned_workers(binary, token, controller, known)
    known.update(rows); result = []
    for pid, saved in list(known.items()):
        row = rows.get(pid)
        if row is not None:
            require(row["starttime"] == saved["starttime"], "worker PID가 재사용되었습니다")
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    current = proc_stat(pid)
                    require(current["starttime"] == saved["starttime"] and current["pgid"] == pid,
                        "종료 직전 worker 소유가 다릅니다")
                    if current["state"] != "Z":
                        os.killpg(pid, sig)
                    if sig == signal.SIGTERM:
                        time.sleep(min(.1, max(0., expires - time.monotonic())))
                except (FileNotFoundError, ProcessLookupError):
                    break
        while True:
            try:
                waited, status = os.waitpid(pid, os.WNOHANG)
                if waited:
                    result.append(dict(pid=pid, starttime=saved["starttime"], wait_status=status, reaped=True))
                    break
            except ChildProcessError:
                try:
                    current = proc_stat(pid)
                except (FileNotFoundError, ProcessLookupError):
                    result.append(dict(pid=pid, starttime=saved["starttime"], reaped_by_controller=True))
                    break
                require(current["starttime"] == saved["starttime"], "회수 직전 worker PID가 바뀌었습니다")
            if time.monotonic() >= expires:
                raise TimeoutError("소유 worker를 제한시간 안에 회수하지 못했습니다")
            time.sleep(.02)
    require(not find_owned_workers(binary, token, controller, known), "소유 worker가 종료 후 남았습니다")
    return result


def supervise_process(argv, *, worker_binary, directory, deadline_epoch, cap, reserve=SUPERVISOR_RESERVE,
        verify_success=None, started_monotonic=None, child_cap=None):
    """controller의 실제 종료와 별도 세션 worker까지 감독하는 CPU 제어부."""
    from scripts import codex_smoke as smoke
    require(sys.platform == "linux", "이 감독은 Linux 소유 프로세스 확인을 요구합니다")
    began = time.monotonic() if started_monotonic is None else started_monotonic
    stop = min(began + cap, time.monotonic() + deadline_epoch - time.time())
    require(cap > reserve and stop - began > reserve, "감독 종결 여유가 부족합니다")
    directory = Path(directory)
    require(not directory.exists() and not directory.is_symlink() and not any(p.is_symlink() for p in directory.parents),
        "기존 감독 결과와 부분 결과를 보존합니다")
    regular(worker_binary)
    directory.mkdir(parents=True, exist_ok=False)
    token = secrets.token_hex(32); environment = dict(os.environ, **{OWNER_KEY: token})
    process = None; controller = None; known = {}; errors = []; notes = []; deferred = []
    result = dict(schema=SCHEMA, status="SUPERVISOR_STARTED", returncode=9, controller_returncode=None,
        worker_reaping=[], parent_cap_seconds=cap, child_cap_seconds=cap-reserve if child_cap is None else child_cap,
        deadline_epoch=deadline_epoch, owner_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
        original_error=None, cleanup_errors=[], actual_controller_exit_observed=False)
    handlers = {}; old_subreaper = set_subreaper(1); thread = None
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.getsignal(sig)
            if handlers[sig] != signal.SIG_IGN:
                signal.signal(sig, lambda number, frame: deferred.append(number))
        process = subprocess.Popen(list(argv), cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True, bufsize=0)
        smoke._register_owned(process, start_new_session=True)
        controller = proc_stat(process.pid)
        result["controller_identity"] = controller
        def drain():
            try:
                count = 0
                with (directory / "controller.log").open("xb") as stream:
                    for chunk in iter(lambda: process.stdout.read(65536), b""):
                        count += len(chunk)
                        require(count < MAX_BYTES, "controller 로그의 20MB 상한을 넘었습니다")
                        stream.write(chunk)
            except BaseException as exc:
                errors.append(dict(type=type(exc).__name__, message=str(exc)))
        thread = threading.Thread(target=drain, daemon=True); thread.start()
        while True:
            known.update(find_owned_workers(worker_binary, token, controller, known))
            rc = process.poll()
            if rc is not None:
                result.update(controller_returncode=rc, actual_controller_exit_observed=True)
                result["lingering_workers_at_controller_exit"] = list(find_owned_workers(worker_binary, token, controller, known))
                if rc != 0:
                    raise ChildProcessError("controller 실제 종료코드: " + str(rc))
                break
            if deferred:
                raise InterruptedError("감독 중 종료 신호: " + str(deferred))
            if errors:
                raise OSError("controller 로그 저장 실패: " + str(errors))
            if time.monotonic() >= stop - reserve or time.time() >= deadline_epoch - reserve:
                raise TimeoutError("controller 작업 예산이 끝났습니다")
            time.sleep(.05)
        require(not errors, "controller 로그 저장 오류가 있습니다")
    except BaseException as exc:
        result["original_error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
    finally:
        stop = min(stop, time.monotonic()+deadline_epoch-time.time())
        if process is not None:
            try:
                if controller is not None:
                    known.update(find_owned_workers(worker_binary, token, controller, known))
                notes = smoke.stop_process_group(process, min(stop, time.monotonic()+5), time.monotonic)
                require(not any("ERROR" in note for note in notes), "controller 그룹 종료 검산 실패: " + str(notes))
                process.wait(timeout=max(.01, min(5., stop-time.monotonic())))
                result.update(controller_returncode=process.returncode, actual_controller_exit_observed=True)
            except BaseException as exc:
                result["cleanup_errors"].append(dict(type=type(exc).__name__, message=str(exc)[:1000]))
            try:
                if controller is not None:
                    result["worker_reaping"] = cleanup_workers(worker_binary, token, controller, known, stop)
            except BaseException as exc:
                result["cleanup_errors"].append(dict(type=type(exc).__name__, message=str(exc)[:1000]))
            if thread is not None:
                thread.join(timeout=max(.01, min(2., stop-time.monotonic())))
                if thread.is_alive():
                    result["cleanup_errors"].append(dict(type="TimeoutError", message="로그 회수가 끝나지 않았습니다"))
                else:
                    process.stdout.close()
            smoke._forget_owned(process)
        try:
            set_subreaper(old_subreaper)
        except BaseException as exc:
            result["cleanup_errors"].append(dict(type=type(exc).__name__, message=str(exc)))
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    result.update(controller_group_cleanup=notes, worker_identities=list(known.values()), log_errors=errors,
        elapsed_seconds=time.monotonic()-began, deferred_signals=deferred)
    try:
        require(result["original_error"] is None and result["controller_returncode"] == 0
            and result["actual_controller_exit_observed"] and not result["cleanup_errors"] and not errors and not deferred,
            "controller 또는 소유 자식의 실제 종료가 완료되지 않았습니다")
        require(not result.get("lingering_workers_at_controller_exit"), "controller가 소유 worker를 남긴 채 종료했습니다")
        if verify_success is not None:
            result["controller_terminal"] = verify_success()
        require(time.monotonic() < stop, "감독 보고서 저장 전 전체 예산이 끝났습니다")
        result.update(status="SUPERVISOR_CANDIDATE_PENDING_PROCESS_EXIT", returncode=0,
            actual_supervisor_exit_observed=False,
            acceptance_requires="SUPERVISOR_PROCESS_EXIT0_AND_NO_APPEND_ONLY_VETO_AND_ROOT_CAP")
    except BaseException as exc:
        if result["original_error"] is None:
            result["original_error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
    try:
        write_once(directory / "supervisor_receipt.json", result)
        require(read_json(directory / "supervisor_receipt.json") == result, "감독 영수증 재읽기가 다릅니다")
        require(time.monotonic() < stop, "감독 보고서 저장·재읽기가 전체 예산을 넘었습니다")
    except BaseException as exc:
        if result["original_error"] is None:
            result["original_error"] = dict(type=type(exc).__name__, message=str(exc)[:2000])
        result.update(status="SUPERVISOR_FAILURE", returncode=9)
    if result["returncode"] != 0:
        result.update(status="SUPERVISOR_FAILURE", returncode=9)
        append_veto(directory, result)
    result["supervisor_directory"] = str(directory)
    result["_supervisor_context"] = dict(directory=str(directory), monotonic_stop=stop, deadline_epoch=deadline_epoch)
    return result


def check_supervisor_cli(context, stage):
    require(time.monotonic() < context["monotonic_stop"] and time.time() < context["deadline_epoch"],
        "감독 출력·종료 중 전체 예산을 넘었습니다: " + stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    require(not (args.prepare and args.check_only), "준비와 읽기 전용 조회는 함께 지정할 수 없습니다")
    result = prepare() if args.prepare else build_identity()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return 0 if result["status"] == "READY" else 8


if __name__ == "__main__":
    raise SystemExit(main())
