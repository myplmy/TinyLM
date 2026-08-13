#!/usr/bin/env python3
"""실행 배치파일(.bat) 린터 — `run-batch` 스킬의 기계 검증부.

검사 항목
  E(에러) 1  비ASCII 바이트          cmd 코드페이지에서 명령이 깨진다
  E       2  chcp 사용                파이썬 출력이 깨진다
  E       3  escape 안 된 <>|         리다이렉션으로 오작동
  E      3b  `%VAR%` 즉시확장          ★2026-08-13 `%` 전면금지 해제. 미정의 변수는 조용히 사라진다
                                       리터럴 퍼센트는 `%%`. `for %%a` 도 이제 허용
  E       4  train 명령에 --tag 없음  정본 dense/tied 로그·ckpt 를 조용히 덮어쓴다
  W(경고) 5  train 명령에 --accum 없음  기본 8 이라 절반만 학습된다
  W       6  학습 런 전부가 goto ERROR  한 런 실패로 후속 런이 죽는다(결과 007)
  W       7  --no-ckpt + KD + 태그없는 dense 교사  VRAM 15.7GB+ (OOM 위험)
  W       8  커널 + --compile 병용     코드가 SystemExit 로 막지만 배치가 무의미해진다
  W       9  pause / exit /b 누락      더블클릭 실행 시 창이 닫혀 로그를 잃는다
  I(정보) 10 꼬리 판정 안내(echo) 없음  로그를 받아도 무엇을 읽어야 할지 모른다
  W      12  --no-ckpt 런 앞에 timeout 없음   직전 런의 VRAM 이 안 풀려 CUBLAS 오류(결과 037)
  W      13  echo 내용이 로그에 안 남는다      콘솔에만 뜨고 runlog 파일엔 없다 → --note 로 (2026-08-13)
  E      14  !VAR! 인데 지연확장 미설정        변수가 안 풀려 입력 비교가 항상 실패한다 (2026-08-13)
  E      15  실험 배치가 smoketest_logs 로     게이트는 스모크가 아니다. test_result 가 맞다 (2026-08-13)
  E      11  줄끝이 CRLF 가 아님       `.gitattributes` 가 `*.bat text eol=crlf` 로 선언하는데
                                       작업트리가 LF 면 git 이 매번 재작성·경고한다(CRLF 재발 원인).
                                       또 cmd.exe 는 LF-only 배치에서 `goto`/라벨이 드물게 어긋난다.
                                       → `--fix` 로 일괄 교정

★한계: 문법·규약만 본다. **실험설계가 옳은지는 판단하지 않는다**(그건 exp-preflight).

사용법
  python scripts/lint_bat.py                    # 루트의 모든 .bat
  python scripts/lint_bat.py run100m_P026.bat   # 특정 파일
  python scripts/lint_bat.py --fix              # 줄끝(CRLF)만 자동 교정
  종료코드 = 에러 개수 (0 이면 통과)

★왜 CRLF 검사가 여기 있나: 이 저장소에서 줄끝 문제가 **두 번 재발**했다. 원인은 사람이 아니라
  구조였다 — `.gitattributes` 는 .bat 을 CRLF 로 선언하는데, 이 워크플로의 모든 도구
  (샌드박스 편집·파이썬 재작성)가 LF 를 쓴다. 그래서 배치를 고칠 때마다 어긋난다.
  **배치를 고치면 반드시 이 린터를 돌리므로**, 검사를 여기 두면 자동으로 잡힌다.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def lint(path: Path):
    raw = path.read_bytes()
    txt = raw.decode("utf-8", errors="replace")
    lines = txt.splitlines()
    err, warn, info = [], [], []

    # 11. 줄끝(CRLF) — .gitattributes 선언과 작업트리가 일치해야 한다
    if b"\r\n" not in raw and raw.strip():
        err.append("줄끝이 LF 다 — .bat 은 CRLF 여야 한다(`.gitattributes`). "
                   "`python scripts/lint_bat.py --fix` 로 교정")
    elif raw.replace(b"\r\n", b"").count(b"\n"):
        err.append("CRLF 와 LF 가 섞여 있다 — `--fix` 로 교정")

    # 1. 비ASCII
    bad_lines = [(i + 1, ln) for i, ln in enumerate(lines) if any(ord(c) > 127 for c in ln)]
    for ln, s in bad_lines:
        err.append(f"L{ln} 비ASCII 문자: {s.strip()[:60]}")

    # 2. chcp
    for i, ln in enumerate(lines):
        if re.search(r"\bchcp\b", ln, re.I):
            err.append(f"L{i+1} chcp 사용 금지: {ln.strip()[:60]}")

    # 3. escape 안 된 <>|
    for i, ln in enumerate(lines):
        for ch in "<>|":
            if ch in ln and ("^" + ch) not in ln:
                err.append(f"L{i+1} escape 안 된 '{ch}' (echo 면 ^{ch}, 주석이면 다른 표현으로): "
                           f"{ln.strip()[:55]}")
                break

    # ★★3b. `%` — **전면 금지를 2026-08-13 에 해제**하고 위험한 형태만 남긴다.
    #
    #   종전에는 `%` 를 통째로 막았다. 그 대가가 컸다:
    #     · 퍼센트를 못 써서 주석에 "PERCENT SIGN" 같은 우회를 썼다
    #     · `for /f` 를 못 써서 목록 읽기를 전부 파이썬으로 뺐다
    #     · `%~dp0` 를 못 써서 `if not exist run100m.py cd ..\\..` 마커를 발명했다
    #
    #   ★해제해도 되는가 — **불가역적 손상은 없다.** `%` 오용의 실패 모드는
    #   ①문자열이 조용히 사라지거나 ②변수가 안 풀리는 것이고, **둘 다 실행 시점에 드러난다.**
    #   파일을 지우거나 체크포인트를 덮어쓰는 종류가 아니다.
    #
    #   ⚠️ **다만 ①이 정확히 이 저장소가 싫어하는 "조용한 실패" 다.**
    #      `echo cost is 5%production%` 에서 `production` 이 미정의면 **그 구간이 통째로 사라진다.**
    #      그래서 **`%VAR%` 형태만 에러로 남긴다.**
    #
    #   **새 규약**: 리터럴 퍼센트는 `%%` 로 쓴다(cmd 가 `%` 하나로 출력한다).
    #                `for %%a in (...)` 도 이제 허용된다.
    for i, ln in enumerate(lines):
        s = ln
        if s.strip().upper().startswith("REM"):
            continue                      # 주석은 실행되지 않는다
        # `%%` 를 먼저 지운다(리터럴 퍼센트 / for 반복변수 — 둘 다 안전)
        probe = s.replace("%%", "")
        m = re.search(r"%[A-Za-z_][A-Za-z0-9_]*%", probe)
        if m:
            err.append(f"L{i+1} `{m.group(0)}` 즉시확장 변수 — **미정의면 그 구간이 조용히 사라진다.** "
                       f"`!VAR!`(+`setlocal enabledelayedexpansion`)를 쓰거나, 리터럴이면 `%%` 로: "
                       f"{s.strip()[:50]}")
        elif re.search(r"%~", probe):
            warn.append(f"L{i+1} `%~`(경로 수식자) — 동작하지만 이 저장소는 "
                        f"`if not exist run100m.py cd ..\\..` 마커를 표준으로 쓴다: {s.strip()[:45]}")
        elif "%" in probe:
            warn.append(f"L{i+1} 홀수 개의 `%` — 리터럴 퍼센트는 `%%` 로 쓰세요: {s.strip()[:50]}")

    # train 명령 수집
    trains = [(i + 1, ln) for i, ln in enumerate(lines)
              if re.search(r"run100m\.py\s+train", ln)]
    # 실험 변형을 뜻하는 플래그. 이게 하나라도 있으면 정본이 아니므로 --tag 가 필수다.
    VARIANT = ["--mlp-group", "--sparse34", "--kd", "--init-from", "--no-ckpt", "--sched",
               "--anneal-end", "--decay-frac", "--ema", "--lora-rank", "--mlp-film",
               "--ternary-kernel", "--pool-tokens", "--center-weights"]
    for ln, s in trains:
        if "--tag" not in s:
            variants = [v for v in VARIANT if v in s]
            if variants:
                err.append(f"L{ln} 변형 런({', '.join(variants)})에 --tag 없음 → "
                           f"정본을 덮어쓴다: {s.strip()[:50]}")
            else:
                info.append(f"L{ln} --tag 없음. 플래그가 없으니 그 (preset,data,tokens) 의 "
                            f"**정본 기준선**을 쓰는 것으로 봅니다. 의도한 것이면 OK, "
                            f"아니면 --tag 를 붙이세요")
        if "--accum" not in s:
            warn.append(f"L{ln} train 에 --accum 없음 → 기본 8 로 절반만 학습: {s.strip()[:55]}")
        if "--no-ckpt" in s and "--kd" in s and "--kd-teacher-tag" not in s:
            warn.append(f"L{ln} --no-ckpt + KD + dense 교사 = VRAM 15.7GB+ (OOM 위험). "
                        f"긴 런이면 --no-ckpt 를 빼거나 압축교사를 쓰세요")
        if re.search(r"--ternary-kernel", s) and "--compile" in s:
            warn.append(f"L{ln} 커널 + --compile 병용 (코드가 SystemExit 로 중단시킨다)")

    # 6. errorlevel 정책
    if trains:
        gotos = 0
        for ln, _ in trains:
            nxt = lines[ln] if ln < len(lines) else ""     # train 다음 줄
            if re.search(r"if errorlevel 1 goto ERROR", nxt):
                gotos += 1
        if gotos == len(trains) and len(trains) > 1:
            warn.append(f"학습 런 {len(trains)}개 전부 'goto ERROR' → 한 런 실패로 후속이 전부 죽는다. "
                        f"독립 런은 'if errorlevel 1 echo [WARN] ... - continuing' 로 (결과 007)")

    # ★12. --no-ckpt 런 앞에 정착 대기가 없다 (결과 037 §7.3, 2026-08-13 신설)
    #   run_P018_compressed_teacher.bat 은 직전 런 종료 1초 뒤에 --no-ckpt 런을 시작해
    #   CUBLAS_STATUS_EXECUTION_FAILED 로 죽었다. 대기를 넣은 배치는 죽지 않았다.
    #   ⚠️ 이건 "메모리 부족이 다른 창구로 나온 것"이고 OOM 만 찾으면 못 알아본다(함정 29).
    nockpt = [(i + 1, ln) for i, ln in enumerate(lines)
              if re.search(r"run100m\.py\s+train", ln) and "--no-ckpt" in ln]
    if nockpt and len(trains) > 1:
        first_nc = nockpt[0][0]
        prev_train = [ln for ln, _ in trains if ln < first_nc]
        if prev_train:
            between = "\n".join(lines[prev_train[-1]:first_nc - 1])
            if "timeout" not in between:
                warn.append(
                    f"L{first_nc} --no-ckpt 런 앞에 `timeout` 정착 대기가 없다. 직전 학습 런은 "
                    f"L{prev_train[-1]} 이다. Windows/WDDM 이 VRAM 을 수 초 붙잡으므로 여유가 "
                    f"1GB 급인 런은 CUBLAS_STATUS_EXECUTION_FAILED 로 죽는다(결과 037 §7.3). "
                    f"`timeout /t 15 /nobreak` 을 넣으세요")

    # 9. pause / exit
    if "pause" not in txt:
        warn.append("pause 없음 → 더블클릭 실행 시 창이 닫혀 로그를 잃는다")

    # ★9b. 무방비 pause — 2026-08-07 야간큐가 여기서 밤새 멈췄다.
    #   `run_night_queue.bat` 은 `TL_NOPAUSE=1` 을 깔고 자식을 `call` 하는데,
    #   자식의 pause 가 그 변수를 안 보면 **키 입력을 기다리며 큐가 정지**한다.
    #   P045·P046 에는 가드가 있었고 P014C 에만 없었다 — 3개 중 1개를 빠뜨린 것이
    #   7시간짜리 무인 실행을 1시간으로 만들었다. 사람이 기억하는 대신 린터가 본다.
    #   **모든 경로의 pause 가 대상이다**(:BADROOT 같은 오류 경로도 큐를 멈춘다).
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.fullmatch(r"(?i)pause", s):
            err.append(f"L{i+1} 무방비 `pause` → 야간큐(`TL_NOPAUSE=1`)가 여기서 멈춘다. "
                       f"`if not defined TL_NOPAUSE pause` 로 바꾸세요")
        elif re.search(r"(?i)\bpause\b", s) and "TL_NOPAUSE" not in s and not s.startswith("REM"):
            warn.append(f"L{i+1} pause 가 TL_NOPAUSE 가드 없이 쓰였다: {s[:55]}")
    if "exit /b" not in txt and "goto ERROR" in txt:
        warn.append("goto ERROR 는 있는데 'exit /b 0' 이 없음 → 정상 종료도 ERROR 블록으로 흘러간다")

    # ★9c. runlog.py 에 `--note` 와 실행 명령을 **한 줄에** 준 것.
    #   2026-08-07 `run_P047_stage0_spam_rate.bat` 이 이 형태였고, runlog 가 note 만 쓰고
    #   **명령을 조용히 버렸다.** 종료코드 0 이라 `if errorlevel 1` 도 안 걸려
    #   **두 단계가 "성공" 으로 끝났는데 로그는 84바이트뿐**이었다.
    #   runlog.py 쪽에도 거절을 넣었지만(이중 방어), 배치 작성 시점에 잡는 게 더 값싸다.
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith("REM"):
            continue          # 주석은 이 규칙의 대상이 아니다(사고를 서술한 문장이 걸렸다)
        if "runlog.py" in ln and "--note" in ln and re.search(r"\s--\s", ln):
            err.append(f"L{i+1} runlog.py 에 --note 와 실행 명령을 함께 줬다 → "
                       f"**명령이 실행되지 않는다**(조용한 무동작). 두 줄로 나누세요: "
                       f"{ln.strip()[:45]}")

    # ★9d. runlog `--name` 에 실험계획 번호가 없다.
    #   야간큐 v2 가 `--name mC_g16` 로 돌아 로그가 `log_20260807_mC_g16.txt` 가 됐고
    #   사용자가 `029_log_..._P045_mC_g16.txt` 로 손수 고쳐야 했다(2026-08-07 지적).
    #   `scripts/batch/` 의 도구는 `!TL_LOGNAME!` 로 **호출자가** 이름을 주므로 대상 아님.
    if path.name.startswith("run_"):
        for i, ln in enumerate(lines):
            if ln.strip().upper().startswith("REM"):
                continue
            m = re.search(r"--name\s+([^\s\"]+)", ln)
            if m and not re.match(r"^(P\d{3}|!)", m.group(1)):
                warn.append(f"L{i+1} runlog --name '{m.group(1)}' 에 계획번호(P0NN)가 없다 → "
                            f"로그 파일명만 보고 어느 실험인지 알 수 없다")

    # 10. 꼬리 판정 안내
    tail = "\n".join(lines[-25:]).lower()
    if not any(k in tail for k in ("record", "read", "decision", "compare", "gate", "verdict")):
        info.append("꼬리에 판정/읽는 순서 안내 echo 가 없다 → 로그를 받아도 해석 기준이 없다")

    # ★★13. **콘솔에만 나오고 로그에는 안 남는 내용** (2026-08-13 사용자 지적)
    #   `runlog.py` 는 자기가 **실행한 것**만 기록한다. 배치가 `echo` 로 찍는 헤더·경고·
    #   "읽는 순서" 는 **cmd 창에만 뜨고 로그에는 한 줄도 안 남는다.**
    #   → `run_recover_dense_best.bat`(P054)이 정확히 그랬다: 콘솔에는 "정본을 덮어쓰지
    #     않는다 / 3.7797 과 비교하라 / copy 명령" 이 다 떴는데 **로그 309줄 어디에도 없다.**
    #   그러면 로그를 나중에 읽는 사람(=다음 세션의 AI)은 **판정 기준을 못 본다.**
    #
    #   ★고칠 방법은 중복이 아니다. `runlog.py --note` 는 **로그와 콘솔에 동시에** 쓴다
    #   (`sys.stdout.write(body)`). 즉 `echo X` → `--note "X"` 는 **1:1 치환**이고
    #   같은 문장을 두 곳에 적는 것이 아니다(그건 함정 18 이 된다).
    #
    #   허용: `echo.`(빈 줄) · 구분선(`=`,`-`) · `@echo off` · 실패 라벨 블록 안
    #   (실패 안내는 자식 프로세스가 이미 죽은 뒤라 runlog 를 못 태울 수 있다)
    if path.name.startswith("run_") and "runlog.py" in txt:
        in_fail_label = False
        for i, raw in enumerate(lines):
            s = raw.strip()
            if re.match(r"^:\w+", s):
                in_fail_label = True          # 라벨 이후는 대개 실패 경로
            if in_fail_label or s.upper().startswith("REM") or s.startswith("@"):
                continue
            m = re.match(r"^echo\s+(.*)$", s, re.I)
            if not m:
                continue
            body = m.group(1)
            # 구분선·장식만 있는 줄은 정보가 아니다
            if not re.sub(r"[=\-_*.!\s^<>]", "", body):
                continue
            warn.append(
                f"L{i+1} 이 echo 내용은 **콘솔에만 뜨고 로그에 안 남는다**: {body[:52]!r} → "
                f"`python scripts\\runlog.py --name P0NN_x --note \"...\"` 로 바꾸세요"
                f"(--note 는 로그와 콘솔에 동시에 쓴다 = 중복 아님)")

    # ★14. `!VAR!` 를 쓰는데 `setlocal enabledelayedexpansion` 이 없다
    #   2026-08-13 실사고: `run_cleanup_checkpoints.bat` 이 `if not "!TL_OK!"=="YES"` 를 썼는데
    #   지연확장이 꺼져 있어 **문자열 "!TL_OK!" 와 "YES" 를 비교**했다. 항상 불일치 →
    #   **YES 를 입력해도 CANCEL 로 갔다.** 조용히 아무것도 안 하는 실패다.
    #   이 저장소는 `%` 를 금지하므로 `!VAR!` 가 **유일한 변수 확장 수단**이고, 따라서
    #   `setlocal enabledelayedexpansion` 누락은 **구조적으로 재발한다.**
    # ★★15. **실험 게이트 로그를 `smoketest_logs` 로 보내지 않는다** (2026-08-13 사용자 지적)
    #   > *"실험과 관련된 게이트를 자꾸 smoke test 로 치부하여 smoketest_logs 에 저장하는데
    #   >  실험 게이트 로그를 test_result 에 실험결과 로그 형태로 저장하도록 할 것."*
    #
    #   ★지적이 맞다. `TL_OUTDIR=smoketest_logs` 는 **`run_smoke_check.bat` 하나만** 쓰라고
    #   만든 것이다(2026-08-07: 스모크 로그가 test_result 를 오염시켰다). 그런데 나는
    #   **P049 단계0·F-1 단계A·P014C 단계2 를 "게이트니까 스모크" 로 분류**해 같은 폴더로 보냈다.
    #
    #   ⚠️ **그건 스모크가 아니라 실험이다.** 계획서의 단계이고, 결과문서에 자리가 있고,
    #      **판정이 후속 런을 막거나 연다.** 실제로 P049 단계0 이 **G0-c 실패로 5.8h 를 막았고**,
    #      그건 `test_result/041` 에 있어야 할 결과다(사용자가 손으로 옮겼다).
    #
    #   **구분 규칙**: `--name` 이 실험계획 번호(P0NN, P000 제외)로 시작하면 **실험 로그**다.
    if "TL_OUTDIR=smoketest_logs" in txt.replace(" ", ""):
        exp = re.findall(r"--name\s+(P\d{3})", txt)
        real = [n for n in exp if n != "P000"]
        if real:
            err.append(f"실험 배치({', '.join(sorted(set(real)))})가 `TL_OUTDIR=smoketest_logs` 를 "
                       f"설정한다 → 게이트 로그가 스모크 폴더로 간다. **게이트는 스모크가 아니다** "
                       f"(계획서 단계이고 판정이 후속 런을 막는다). 그 줄을 지우면 test_result 로 간다")

    if re.search(r"![A-Za-z_]\w*!", txt) and "enabledelayedexpansion" not in txt.lower():
        err.append("`!VAR!` 를 쓰는데 `setlocal enabledelayedexpansion` 이 없다 → "
                   "변수가 안 풀려 **문자열 그대로 비교**된다(입력이 항상 불일치). "
                   "파일 앞에 `setlocal enabledelayedexpansion` 을 넣으세요")

    return err, warn, info


def fix_eol(path: Path) -> bool:
    """줄끝을 CRLF 로 정규화. 내용은 건드리지 않는다."""
    raw = path.read_bytes()
    out = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if out != raw:
        path.write_bytes(out)
        return True
    return False


def main():
    args = [a for a in sys.argv[1:] if a != "--fix"]
    do_fix = "--fix" in sys.argv[1:]
    files = [Path(a) if Path(a).is_absolute() else ROOT / a for a in args] or \
            sorted(list(ROOT.glob('*.bat')) + list((ROOT / 'scripts' / 'batch').glob('*.bat')))
    if do_fix:
        n = sum(fix_eol(f) for f in files if f.exists())
        print(f"[--fix] 줄끝을 CRLF 로 교정: {n}개 (내용 변경 없음)")
    if not files:
        print("점검할 .bat 이 없습니다.")
        return 0
    total_err = 0
    for f in files:
        if not f.exists():
            print(f"[!] {f} 없음"); continue
        err, warn, info = lint(f)
        total_err += len(err)
        mark = "FAIL" if err else ("WARN" if warn else "OK")
        print(f"\n=== {f.name}  [{mark}]  (E{len(err)} W{len(warn)} I{len(info)})")
        for m in err:
            print(f"  [E] {m}")
        for m in warn:
            print(f"  [W] {m}")
        for m in info:
            print(f"  [i] {m}")
    print(f"\n총 에러 {total_err}건")
    print("주의: 이 린터는 문법·규약만 봅니다. 실험설계 검증은 exp-preflight 스킬로.")
    return total_err


if __name__ == "__main__":
    sys.exit(main())
