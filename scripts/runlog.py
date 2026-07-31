#!/usr/bin/env python3
"""실행 로그 티(tee) — **콘솔에 실시간 출력하면서 `test_result/` 에 즉시 기록**한다.

★왜 필요한가 (사용자 요구, 2026-07-31)
  지금까지 실험 로그는 **사용자가 콘솔에서 복사해 붙여넣는** 방식이었다. 그래서
    · 중간에 크래시하면 그때까지의 출력이 **스크롤 버퍼에만** 남고
    · 장시간 런(P033 은 18~28h)에서는 버퍼를 넘겨 **앞부분이 통째로 사라지며**
    · 붙여넣기 과정에서 잘림·누락이 생긴다.
  **장기 실험에서 로그 유실은 그 시간 전체를 날리는 것과 같다.**

★유실 방지 설계 (이 파일의 존재 이유)
  1. **줄 단위 즉시 기록 + flush** — 버퍼에 쌓아두지 않는다.
  2. **주기적 `os.fsync()`**(기본 2초) — OS 캐시까지 디스크로 내린다.
     BSOD·정전·강제종료에서도 마지막 몇 초를 제외한 전부가 남는다.
  3. **`finally` 로 꼬리말 보장** — 예외·Ctrl+C·자식 프로세스 이상종료 어디서든
     종료코드와 소요시간이 기록된다.
  4. **append 모드가 기본** — 한 배치의 여러 단계가 **한 파일에 누적**된다.
     3단계에서 죽어도 1~2단계 로그는 그대로 남는다.
  5. **인코딩 사고 차단** — 자식에게 `PYTHONIOENCODING=utf-8` 을 강제해 파이프를
     UTF-8 로 고정하고, 파일은 UTF-8, 콘솔은 파이썬이 콘솔 API 로 직접 쓴다.
     (파이프일 때 파이썬 기본 인코딩은 locale=cp949 라 한글이 깨질 수 있다)

★2026-07-31 수정 — **콘솔과 로그파일이 달랐다**(사용자 보고)
  이 래퍼는 **감싼 파이썬 명령의 출력만** 기록한다. 그래서 배치의 `echo` 로 찍히는
  **단계 제목·판정 안내·WHAT TO RECORD 블록이 로그파일에 전혀 남지 않았다.**
  콘솔에는 있고 파일에는 없으니 두 개가 다르게 보이는 것이 당연했다 — 사용자가 계속
  콘솔을 복사해 붙여 온 이유가 이것이다. 세 가지를 고쳤다.

  1. **`--note`** — 명령을 실행하지 않고 **텍스트만** 콘솔과 로그에 동시에 남긴다.
     배치의 단계 제목·판정 안내를 이걸로 흘려보내면 **로그파일만 읽어도 맥락이 산다.**
       python scripts/runlog.py --name P035 --note "[1/2] step anneal at 0.60"
  2. **줄끝을 os.linesep 으로** — 종전에는 `newline=""` 라 파일이 **LF 전용**이었다.
     Windows 메모장·일부 편집기에서 **한 줄로 붙어 보였다**(콘솔과 또 다르게 보이는 원인).
  3. **기록 후 검증** — 닫은 뒤 파일 존재·크기를 다시 확인하고 콘솔에 찍는다.
     0바이트거나 사라졌으면 **경고한다**. "로그 파일: ..." 만 찍고 실제로는 없는
     상황을 조용히 넘기지 않는다.

사용법 — `--` 뒤가 실행할 명령이다
  python scripts/runlog.py --name P030-stage2B -- python scripts/diag_kvcache.py --device cpu
  python scripts/runlog.py --name P036-trapping --num 018 -- python scripts/diag_trapping.py
  python scripts/runlog.py --name P035 --note "[1/2] ..." "control = qb_wsd60"

파일명
  `test_result/{num}_log_{YYYYMMDD}_{name}.txt`   (--num 있을 때)
  `test_result/log_{YYYYMMDD}_{name}.txt`         (없을 때 — 결과문서 쓸 때 번호를 붙인다)

★같은 날 같은 이름이면 **한 파일에 이어 붙는다**. 세션 배너로 구분되므로
  재실행해도 이전 로그가 사라지지 않는다.

종료코드 = 자식 프로세스의 종료코드 그대로(배치의 `if errorlevel` 이 그대로 동작한다).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test_result"


def _split_argv(argv):
    """`--` 앞은 이 스크립트 옵션, 뒤는 실행할 명령. argparse 의 REMAINDER 는 까다로워 직접 나눈다."""
    if "--" not in argv:
        return argv, []
    i = argv.index("--")
    return argv[:i], argv[i + 1:]


def _verify(path):
    """★기록 후 실제로 파일이 남았는지 확인한다.

    종전에는 `finally` 가 "로그 파일: ..." 를 **무조건** 찍었다. 그래서 파일이 만들어지지
    않았거나 곧바로 사라져도(동기화 지연·백신·수동 삭제) **콘솔은 성공한 것처럼 보였다.**
    경로만 믿지 말고 크기까지 찍는다.
    """
    try:
        if not path.exists():
            sys.stdout.write(f"[runlog] ★경고: 로그 파일이 존재하지 않는다 — {path}\n"
                             f"[runlog]   경로 권한·동기화·백신을 확인할 것. "
                             f"콘솔 출력이 유일한 사본이다.\n")
            return
        n = path.stat().st_size
        sys.stdout.write(f"[runlog] 로그 파일: {path}  ({n:,} bytes)\n")
        if n == 0:
            sys.stdout.write("[runlog] ★경고: 0바이트다. 기록이 실패했다.\n")
    except OSError as e:                     # noqa: BLE001
        sys.stdout.write(f"[runlog] ★경고: 로그 파일 확인 실패 — {type(e).__name__}: {e}\n")
    sys.stdout.flush()


def main():
    own, cmd = _split_argv(sys.argv[1:])
    ap = argparse.ArgumentParser(description="실행 로그 tee (콘솔 + test_result 즉시 기록)")
    ap.add_argument("--name", required=True, help="로그 파일명에 들어갈 실험 이름(예: P030-stage2B)")
    ap.add_argument("--num", default=None, help="결과 번호를 미리 아는 경우(예: 018)")
    ap.add_argument("--fsync-sec", type=float, default=2.0,
                    help="디스크 동기화 주기(초). 0 이면 매 줄마다 — 느리지만 가장 안전")
    ap.add_argument("--no-append", action="store_true",
                    help="같은 파일이 있어도 덮어쓴다(기본은 이어쓰기 = 유실 방지)")
    ap.add_argument("--note", nargs="+", default=None,
                    help="명령 대신 텍스트만 기록한다(배치의 단계 제목·판정 안내용). 여러 개면 여러 줄")
    a = ap.parse_args(own)

    if not cmd and not a.note:
        print("[runlog] 실행할 명령이 없습니다. `--` 뒤에 명령을 주거나 --note 를 쓰세요.",
              file=sys.stderr)
        print("  예) python scripts/runlog.py --name X -- python run100m.py train ...", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    stem = f"{a.num}_log_{day}_{a.name}" if a.num else f"log_{day}_{a.name}"
    path = OUT / f"{stem}.txt"

    # ── --note : 명령 없이 텍스트만. 배치의 echo 블록을 로그에도 남기는 통로다. ──
    if a.note:
        body = "".join(f"{ln}\n" for ln in a.note)
        with open(path, "a", encoding="utf-8", newline=os.linesep) as nf:
            nf.write(body)
            nf.flush()
            os.fsync(nf.fileno())
        sys.stdout.write(body)
        sys.stdout.flush()
        _verify(path)
        return 0

    started = datetime.now()
    t0 = time.time()
    # 자식이 파이프로 출력하면 파이썬 기본 인코딩이 locale(cp949) 이 되어 한글이 깨진다.
    # UTF-8 로 못박고, 버퍼링도 끈다(-u 와 동일 효과).
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")

    mode = "w" if a.no_append else "a"
    # ★newline=os.linesep — 종전 `newline=""` 는 자식이 보낸 `\n` 을 그대로 써서 파일이
    #   **LF 전용**이 됐다. Windows 메모장에서 전부 한 줄로 붙어 보이고, 콘솔과 또 다르게
    #   보이는 원인이었다. universal-newlines 로 이미 `\n` 로 정규화된 뒤이므로 여기서
    #   플랫폼 줄끝으로 되돌리는 것이 맞다.
    f = open(path, mode, encoding="utf-8", newline=os.linesep)
    rc = -1
    try:
        head = (f"\n{'=' * 78}\n"
                f"[runlog] {started:%Y-%m-%d %H:%M:%S}  name={a.name}\n"
                f"[runlog] cwd={os.getcwd()}\n"
                f"[runlog] cmd={' '.join(cmd)}\n"
                f"{'=' * 78}\n")
        f.write(head); f.flush()
        sys.stdout.write(head); sys.stdout.flush()

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=env, bufsize=1, text=True,
                                encoding="utf-8", errors="replace")
        last_sync = time.time()
        assert proc.stdout is not None
        for line in proc.stdout:            # 줄 단위 — 버퍼에 쌓지 않는다
            sys.stdout.write(line)
            sys.stdout.flush()              # 콘솔 실시간
            f.write(line)
            f.flush()                       # 파일 실시간(파이썬 버퍼 비움)
            now = time.time()
            if a.fsync_sec <= 0 or now - last_sync >= a.fsync_sec:
                os.fsync(f.fileno())        # ★OS 캐시까지 디스크로 — 정전·BSOD 대비
                last_sync = now
        rc = proc.wait()
    except KeyboardInterrupt:
        rc = 130
        msg = "\n[runlog] ★Ctrl+C 로 중단됨 — 여기까지의 로그는 보존됩니다.\n"
        f.write(msg); sys.stdout.write(msg)
    except Exception as e:                   # noqa: BLE001 — 어떤 예외든 꼬리말은 남긴다
        rc = 1
        msg = f"\n[runlog] ★래퍼 예외: {type(e).__name__}: {e}\n"
        f.write(msg); sys.stdout.write(msg)
    finally:
        el = time.time() - t0
        tail = (f"{'-' * 78}\n"
                f"[runlog] 종료코드 {rc}  소요 {el/60:.1f}분  "
                f"({datetime.now():%Y-%m-%d %H:%M:%S})\n"
                f"{'=' * 78}\n")
        try:
            f.write(tail); f.flush(); os.fsync(f.fileno())
        finally:
            f.close()
        sys.stdout.write(tail); sys.stdout.flush()
        _verify(path)                    # ★경로만 찍지 않는다 — 실제로 남았는지 본다
    return rc


if __name__ == "__main__":
    sys.exit(main())
