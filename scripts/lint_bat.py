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
  E      16  TL_OUTDIR 을 깔면서 안 치운다      뒤 배치로 새어 나가 로그 폴더가 오염된다 (2026-08-13)
  W      17  재실행본인데 단계명이 그대로      로그가 이전 측정과 한 파일에 섞인다. stage0b 로 (2026-08-13)
  E      18  빈 배치 / 실행문 없음             ★0바이트 파일이 모든 검사를 통과해 큐가 조용히 건너뛴다 (2026-08-13)
  E      23  --no-ckpt + --train-repeat ^> 2.0   ★실측(방문 36회) 밖 외삽. 결과 058 이 OOM (2026-08-31)
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


# ★설계상 매 세션 같은 이름으로 다시 도는 배치 — 규칙 9d·19 의 대상이 아니다(2026-08-28).
_RERUN_BY_DESIGN = {"run_smoke_check.bat"}

# ★★규칙 23 — `--no-ckpt` 활성 예산은 **방문 수가 아니라 `M x 방문`** 이다.
#   `M = micro_bs x seq` 가 속도·VRAM 을 동시에 정한다(결과 007). 활성값은 그 곱에 붙는다.
#
#   실측 세 점(cla2 몸통, 무KD, `--no-ckpt`):
#     M 8192 x 20방문 = 163,840  ->  reserved  8.89 GB
#     M 8192 x 36방문 = 294,912  ->  reserved 12.59 GB   <- ★확인된 최대
#     M 8192 x 52방문 = 425,984  ->  🚫OOM(14.67 GiB 에서 실패, 결과 058)
#   기울기 (12.59-8.89)/(294,912-163,840) = 2.82e-5 GB per token-visit.
#
#   🚫**중간값을 예측하지 않는다**(함정 34) — **확인된 최대 294,912 를 문턱으로 쓴다.**
#   ⚠️절편(가중치·옵티마이저)은 M 에 안 붙으므로 이 곱은 **근사**다. 린터의 안전선이지
#      VRAM 모형이 아니다. 정확한 모형은 기준표 B.13 에 있다.
NOCKPT_MAX_MV = 294_912
DEFAULT_MICRO_BS, DEFAULT_SEQ = 8, 1024


def _visits(preset: str, repeat: float):
    """prelude + middle x R + coda. 프리셋을 못 읽으면 None.

    🚫**층수를 여기 하드코딩하지 않는다**(함정 18) — `tinylm/config.py` 가 정본이다.
    패키지 `__init__` 을 거치지 않고 파일에서 직접 로드해 **torch 의존을 만들지 않는다.**
    """
    global _PRESETS
    if _PRESETS is None:
        try:
            import importlib.util
            name = "_tinylm_cfg_for_lint"
            spec = importlib.util.spec_from_file_location(
                name, ROOT / "tinylm" / "config.py")
            mod = importlib.util.module_from_spec(spec)
            # ⚠️`@dataclass` 는 `sys.modules[cls.__module__]` 를 읽는다 —
            #   등록 전에 exec 하면 AttributeError 로 조용히 실패한다.
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            _PRESETS = mod.PRESETS
        except Exception:                                 # noqa: BLE001
            _PRESETS = {}
    fn = _PRESETS.get(preset)
    if fn is None:
        return None
    try:
        c = fn(1024, True)
        return int(c.n_prelude + round(c.n_middle * repeat) + c.n_coda)
    except Exception:                                     # noqa: BLE001
        return None


_PRESETS = None


def lint(path: Path):
    raw = path.read_bytes()
    txt = raw.decode("utf-8", errors="replace")
    lines = txt.splitlines()
    err, warn, info = [], [], []

    # ★★18. **빈 배치 / 실행문 없음** (2026-08-13 실사고)
    #   `run_smoke_check.bat` 이 **0바이트**가 됐는데 **모든 검사를 통과**했다.
    #   빈 파일에서는 비ASCII도, `%`도, `--tag` 누락도 **아무것도 걸리지 않는다.**
    #   그리고 `queue_menu.py` 는 **파일 존재만** 보므로 메뉴에 정상 표시되고,
    #   큐는 `call` 후 즉시 반환해 **`[queue] done` 을 찍는다** — 조용히 건너뛴다.
    #
    #   ★원인은 내 편집 도구였다: `pathlib.Path.write_text()` 는 **먼저 truncate 하고**
    #     그 다음에 인코딩한다. `encoding="ascii"` 로 비ASCII 문자를 쓰려다 실패하면
    #     **파일이 0바이트로 남는다.** 그리고 그 상태가 커밋까지 됐다.
    #   → 규칙: **인코딩을 먼저 검증하고(`.encode()`), 성공했을 때만 `write_bytes()`.**
    if not raw.strip():
        err.append("★**빈 파일이다(0바이트).** 큐가 조용히 건너뛰고 `[queue] done` 을 찍는다. "
                   "편집 도구가 파일을 파괴했을 수 있다(`write_text` 는 먼저 truncate 한다) — "
                   "`git show <commit>:<path>` 로 복원할 것")
        return err, warn, info
    if not [ln for ln in lines
            if ln.strip() and not ln.strip().upper().startswith("REM")
            and not ln.strip().startswith("@")]:
        err.append("★**실행문이 하나도 없다**(주석·`@echo off` 뿐). 큐가 조용히 건너뛴다")

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

    # 1b. ★제어문자 (2026-08-30 신설) — **ASCII 이지만 명령을 깨뜨린다**
    #   🚫`run_P067_stage2a_gemma_probe-done.bat` 에 **백스페이스(0x08)와 탭(0x09)** 이 박혀 있었다.
    #   부르려던 것은 `scripts` + 역슬래시 + `batch` + 역슬래시 + `tool_wandb_push.bat` 인데,
    #   파이썬 패치 스크립트가 그 역슬래시 둘을 **이스케이프로 해석**해 제어문자로 바꿔 버렸다.
    #   ★**결과: 그 배치의 wandb push 가 한 번도 안 돌았다** — 종료코드는 정상이었다.
    #   🚫**규칙 1(비ASCII)은 이것을 못 잡는다.** 0x08·0x09 는 ASCII 다.
    #   ⚠️탭도 금지한다 — 배치에서 쓸 이유가 없고 위와 같은 사고의 흔적이다.
    for i, ln in enumerate(lines):
        bad = [(j, ord(c)) for j, c in enumerate(ln) if ord(c) < 32]
        if bad:
            names = ", ".join(f"0x{o:02x}@{j}" for j, o in bad[:4])
            err.append(f"L{i+1} 제어문자 {names} — 파이썬 패치가 백슬래시 이스케이프를 "
                       f"해석한 흔적이다: {ln.strip()[:50]!r}")

    # 1c. ★★홀로 있는 CR (2026-08-30 신설) — **규칙 1b 가 못 잡는다**
    #   🚫`tool_smoke.bat` 의 팔 [17]·[18] 이 `python scripts` + CR + `unlog.py` 였다.
    #   파이썬 패치가 역슬래시-r 을 **CR 로 해석**한 것이고, 그 둘은 통째로 죽었다.
    #   ★규칙 1b 는 `splitlines()` 된 문자열을 보는데, **그 CR 이 바로 줄을 잘라**
    #   잘린 두 조각에는 제어문자가 없었다. → **원본 바이트를 따로 본다.**
    #   CRLF 는 정상이고 **홀로 있는 CR 만** 에러다.
    _raw = raw          # 54행에서 이미 읽었다
    _lone = [k for k, ch in enumerate(_raw)
             if ch == 13 and (k + 1 >= len(_raw) or _raw[k + 1] != 10)]
    if _lone:
        _ln = _raw[:_lone[0]].count(b"\n") + 1
        err.append(f"L{_ln} 홀로 있는 CR {len(_lone)}개(offset {_lone[:3]}) — "
                   "파이썬 패치가 역슬래시-r 을 CR 로 해석했다. "
                   "`scripts` + CR + `unlog.py` 가 전형적인 모양이다")

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
    # ★★2026-09-02 — **주석은 명령이 아니다.** 종전에는 REM 에 명령 이름을 적기만 해도
    #   규칙 5·21 이 발화했다. 배치 헤더가 설계 근거를 남기는 자리인데
    #   거기 `run100m.py train` 이라고 쓰면 오탐이 나서 **설명을 못 쓰게** 만들었다.
    def _is_comment(x: str) -> bool:
        y = x.strip()
        return y.upper().startswith("REM") or y.startswith("::")

    trains = [(i + 1, ln) for i, ln in enumerate(lines)
              if re.search(r"run100m\.py\s+train", ln) and not _is_comment(ln)]
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
        # ── ★규칙 23 (2026-08-31 신설) — **`--no-ckpt` 를 실측 방문 수 밖으로 외삽하지 않는다**
        #   결과 058: `--no-ckpt --train-repeat 3.0` 이 **1.4분 만에 CUDA OOM**(14.67 GiB).
        #   실측은 `--train-repeat 2.0`(m100 계열 -> 방문 36회, 13.73 GiB)까지뿐인데
        #   그 여유를 **방문 52회에 그대로 옮겨 적었다.** 🚫*"볼록성은 법칙이 아니다 —
        #   안 잰 점을 예측하지 않는다"*(2026-08-26) 의 정확한 재발이다.
        #
        #   ★**세는 것은 배수가 아니라 방문 수**다: prelude + middle x R + coda.
        #   얇은 몸통(m100s8)에서 R=3.0 은 방문 28회로 **실측 안**이다 —
        #   배수로 자르면 그 배치를 헛되이 막는다(이 규칙의 첫 초안이 실제로 그랬다).
        #   ⚠️이 규칙은 **에러**다. 3.6시간짜리 런이 통째로 날아가는 값이라 경고로 두지 않는다.
        # ⚠️`-done` 은 **이미 돌아간 배치**다. 규칙 23 은 *돌리기 전* 규칙이므로 건너뛴다 —
        #   실패한 런의 배치는 기록으로 남기는 것이 규약이고(결과 058·060), 그것이
        #   영구히 빨간불이면 **새 위반을 가린다**(경보 피로).
        m_tr = re.search(r"--train-repeat\s+([0-9.]+)", s)
        if "--no-ckpt" in s and m_tr and not path.name.endswith("-done.bat"):
            m_ps = re.search(r"--preset\s+(\S+)", s)
            v = _visits(m_ps.group(1) if m_ps else "m100", float(m_tr.group(1)))
            m_mb = re.search(r"--micro-bs\s+(\d+)", s)
            m_sq = re.search(r"--seq\s+(\d+)", s)
            M = (int(m_mb.group(1)) if m_mb else DEFAULT_MICRO_BS) * \
                (int(m_sq.group(1)) if m_sq else DEFAULT_SEQ)
            if v is None:
                warn.append(f"L{ln} --no-ckpt + --train-repeat 인데 프리셋 층수를 못 읽었다 "
                            f"— `M x 방문` 을 손으로 확인하세요(실측 한계 {NOCKPT_MAX_MV:,})")
            elif M * v > NOCKPT_MAX_MV:
                err.append(
                    f"L{ln} --no-ckpt 활성 예산 초과: M {M:,} x 방문 {v}회 = "
                    f"**{M * v:,}** ^> 확인된 최대 {NOCKPT_MAX_MV:,} = **실측 밖 외삽**. "
                    f"294,912(=8192x36) 가 12.59 GB 였고 425,984(=8192x52) 는 "
                    f"결과 058 에서 OOM 했다. ★**M 을 줄이면 통과한다** — "
                    f"`--micro-bs` 를 반으로 하고 `--accum` 을 두 배로 하면 "
                    f"유효배치가 그대로다. 아니면 --no-ckpt 를 빼거나 250스텝 프로브로 재세요")

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
    # ★2026-08-28 — 규칙 9d 는 **실험 배치**를 위한 것이다. 스모크는 계획번호가 없는 것이
    #   맞고(도구다), 규칙 본문도 *"도구·진단 로그는 P번호가 없을 수 있다"* 고 적고 있다.
    #   그런데 검사가 그 예외를 구현하지 않아 **매 세션 경고 1건**을 냈다.
    if path.name.startswith("run_") and path.name not in _RERUN_BY_DESIGN:
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

    # ★★16. `TL_OUTDIR` 을 설정하는 배치는 **끝나기 전에 반드시 비운다** (2026-08-13 실사고)
    #   사용자 보고: `run_queue.bat` 으로 0 1 2 3 을 돌렸더니 **네 로그가 전부**
    #   `smoketest_logs` 로 갔다. 실험 배치 셋은 `TL_OUTDIR` 을 설정하지 않는데도 그랬다 —
    #   id 0(`run_smoke_check.bat`)이 깐 값이 뒤로 새어 나간 것이다.
    #   `setlocal` 이 있었는데도 그랬으므로 **`setlocal` 만으로는 부족하다.**
    #   ⚠️ 조용한 실패다 — 로그는 잘 써지고 종료코드도 0 이다. 폴더만 틀리다.
    # ★17. **재실행본인데 단계명이 그대로다** (2026-08-13 사용자 지시)
    #   `runlog.py` 의 실험 로그는 `{번호}_log_{YYYYMMDD}_{name}.txt` 이고 **같은 날 같은
    #   이름이면 이어쓴다**(한 배치의 여러 단계를 모으려는 설계). 그래서 **도구를 고치고
    #   같은 이름으로 다시 돌리면 두 측정이 한 파일에 섞인다.**
    #   실제로 P049 stage0(난수 정답, 무효)과 P055 stage0(퇴화 데이터, 무효)이 그랬다.
    #   → 재실행본은 `stage0b` 처럼 **단계명에 b/c 를 붙인다**(ai_dev_tool/03 §7).
    #
    #   판정: 헤더에 RE-RUN 계열 단어가 있는데 `--name` 의 단계 토큰에 b/c 가 없으면 경고.
    # ★★20. **`[VERIFY]`(계약 검사) 뒤에 학습 런이 오면 안 된다** (2026-08-22 실사고)
    #   `tool_smoke.bat` 에 팔 [9](sm_wqbf16)를 추가하면서 **패턴으로 삽입**했더니
    #   `rindex("if errorlevel 1 echo [WARN]")` 가 **VERIFY 블록 뒤를 잡았다.**
    #   → 팔은 돌았는데 **`check_smoke.py` 가 그 전에 실행**돼 *"json 이 없다"* 로 FAIL.
    #   ⚠️**조용한 실패가 아니라 시끄러운 오탐**이었지만, 반대로 **팔이 죽어도 못 알아본다.**
    #   ★규칙: **계약 검사는 언제나 마지막 학습 런 뒤**에 온다.
    _vi = txt.find("check_smoke.py")
    if _vi >= 0:
        _after = txt[_vi:]
        if re.search(r"run100m\.py\s+train", _after):
            err.append("★`check_smoke.py`(계약 검사) **뒤에 학습 런이 있다** — 그 팔의 json 은 "
                       "검사 시점에 존재하지 않아 **FAIL 로 오탐**된다. 학습 런을 VERIFY **앞으로** 옮기세요")

    # ── 규칙 21 (2026-08-22 사용자 지시) — ★**무KD 면 `--no-ckpt` 가 기본이다**
    #   결과 051 §2.3: KD 를 빼면 reserved 12.47 -^> 10.31 GiB(여유 5.69)이고
    #   `--no-ckpt` 로 **12.6 -^> 10.0분(-20.6%)**. **안 쓸 이유가 없다.**
    #   🚫**코드 기본값은 바꾸지 않는다** — `grad_ckpt` 는 함정 2 의 비교조건이라
    #   뒤집으면 **기존 런 전부와 비교가 끊긴다.** 그래서 **배치에서** 기본으로 쓴다.
    #   ⚠️36층·재귀는 실측이 없다 -^> 그때는 이 안내를 무시하고 VRAM 확인 런을 먼저 돌린다.
    for _m in re.finditer(r"^.*run100m\.py\s+train\b.*$", txt, re.M):
        _ln = _m.group(0)
        if _is_comment(_ln):
            continue                                   # ★주석은 명령이 아니다
        if "--tiny" in _ln or "synthetic" in _ln:
            continue                                   # 스모크는 대상이 아니다
        if "--kd" in _ln or "--no-ckpt" in _ln:
            continue
        _no = txt[:_m.start()].count("\n") + 1
        info.append(f"L{_no} ★**무KD 학습인데 `--no-ckpt` 가 없다.** 결과 051: "
                   f"reserved 여유 5.69 GiB / 벽시계 **-20.6%**. 2026-08-22 사용자 지시로 "
                   f"**무KD 의 기본은 `--no-ckpt`** 다. ⚠️36층·재귀는 VRAM 실측이 없으니 "
                   f"P065 단계2(250스텝 확인)를 먼저 돌리고 붙이세요")

    # ── ★규칙 24 (2026-09-02 신설, E14/E15) — **`common_bpb` 호출 형태**
    #   ⚠️`--tokenizer-hf` 가 두 도구에서 **다른 규약**이다(함정 28):
    #     `run100m.py train --tokenizer-hf <폴더>`      맨 폴더 하나
    #     `common_bpb.py   --tokenizer-hf TAG=<폴더>`   태그마다 하나
    #   2026-09-02 배치가 학습 형태를 복사해 넣어 **9.2시간 런의 헤드라인 비교가
    #   통째로 날아갔다.** 학습은 이미 끝난 뒤였고 재측정에 1분이면 됐다.
    #   그리고 `common_bpb` 는 **한 호출 안에 모델이 둘 이상**일 때만 비교표를 만든다 —
    #   호출을 나누면 각각 "비교할 모델이 2개 미만" 을 찍고 exit 0 한다(E15).
    for _m in re.finditer(r"^.*common_bpb\.py\b.*$", txt, re.M):
        _ln = _m.group(0)
        if _is_comment(_ln):
            continue                                   # ★주석은 명령이 아니다
        _no = txt[:_m.start()].count("\n") + 1
        _tk = re.search(r"--tokenizer-hf\s+(.+?)(?:\s+--|\s*$)", _ln)
        if _tk:
            for _spec in _tk.group(1).split():
                if "=" not in _spec:
                    # -done 은 이미 돌아간 배치다. 규칙 24 는 *돌리기 전* 규칙이라
                    # 거기서는 기록으로만 남긴다 — 늘 빨간 게이트는 아무도 안 본다.
                    _sink = info if path.name.endswith("-done.bat") else err
                    _sink.append(
                        f"L{_no} ★★`common_bpb.py --tokenizer-hf` 는 **TAG=폴더** 형식이다. "
                        f"받은 것: `{_spec}` — 이건 **`run100m.py train` 쪽 규약**이다(함정 28). "
                        f"`--tokenizer-hf <태그>={_spec}` 로 고치세요. "
                        f"2026-09-02 에 이 한 글자로 9.2시간 런의 판정이 날아갔다")
        _md = re.search(r"--models\s+(.+?)(?:\s+--|\s*$)", _ln)
        if _md and len(_md.group(1).split()) < 2:
            info.append(
                f"L{_no} ★`common_bpb.py` 를 **모델 하나**로 부른다 — 그 호출은 bpb 를 "
                f"인쇄만 하고 **비교표를 안 만든다**(exit 0). 비교가 목적이면 "
                f"**한 호출에 모델을 전부** 넣으세요(E15)")

        # ── ★규칙 24c (2026-09-03 신설, E22) — **외부 토크나이저 = 큰 어휘 = CE 폭발**
        #   `common_bpb` 의 종전 경로는 `F.cross_entropy(l2.float(), y1)` 로
        #   **어휘 전체 위에 fp32 사본을 한 번에** 만든다.
        #     필요 = micro_bs x seq x 어휘 x 4B
        #   2026-09-03 에 gemma 어휘 262,144 x (8 x 1024) x 4B = **정확히 8.00 GiB**
        #   를 요구해 OOM 으로 죽었다(E22). ★**새 결함이 아니라 회귀다** —
        #   단계1d 가 `--micro-bs 2 --ce-chunk 4096` 으로 같은 함정을 이미 넘었고
        #   그 두 플래그가 새 배치로 안 옥겨왔다.
        #   ⚠️`--ce-chunk` 만으로는 절반만 막힌다 — `logits` 자체가 bf16 로
        #   micro_bs 8 이면 4.29 GB 다. ★**`--micro-bs` 도 함께 본다.**
        if _tk:                                        # 외부 토크나이저를 쓰는 호출만
            _sink24c = info if path.name.endswith("-done.bat") else err
            if not re.search(r"--ce-chunk\s+\d+", _ln):
                _sink24c.append(
                    f"L{_no} ★★`common_bpb.py --tokenizer-hf` 인데 **`--ce-chunk` 가 없다**. "
                    f"기본값 0 은 어휘 전체 위에 fp32 사본을 **한 번에** 만든다 — "
                    f"gemma 어휘(262,144)에서는 **8.00 GiB** 로 OOM 이다(E22, 2026-09-03). "
                    f"`--micro-bs 2 --ce-chunk 1024` 를 붙이세요")
            _mb = re.search(r"--micro-bs\s+(\d+)", _ln)
            if _mb and int(_mb.group(1)) > 4:
                _sink24c.append(
                    f"L{_no} ★`common_bpb.py --tokenizer-hf` 에 `--micro-bs {_mb.group(1)}` 은 "
                    f"크다. 큰 어휘에서는 `logits`(bf16) 만으로도 "
                    f"micro_bs x 1024 x 어휘 x 2B 가 된다 — **`--ce-chunk` 로는 절반만 "
                    f"막힌다**. 단계1d 정본은 **`--micro-bs 2`** 다(E22)")

    # ── 규칙 22 (2026-08-22 사용자 지시 §14) — ★**학습 배치는 wandb 로 밀어야 한다**
    #   🚫`trainer.py` 에 훅을 넣지 않는 이유는 `tool_wandb_push.bat` 헤더에 있다:
    #     (1) 훅이 타이밍을 흔든다 — 우리는 0.003 차이로 판정한다
    #     (2) 학습 루프 안의 네트워크 실패가 **몇 시간짜리 런을 죽인다**
    #   → **학습이 끝난 뒤 배치가 부른다.** 그래서 **배치마다 잊을 수 있고**, 이 규칙이 그물이다.
    #   ★2026-09-03 오탐 정정 — 이 규칙도 **주석을 명령으로 읽고 있었다.**
    #   2026-09-02 에 규칙 5·21 을 같은 이유로 고쳤는데 **22 를 빠뜨렸다**(불완전 수정).
    #   배치 헤더에 `run100m.py train` 이라고 **설명**만 써도 발화해서, 학습을
    #   하나도 안 하는 측정 배치가 "학습 배치인데 wandb 가 없다" 를 받았다.
    #   ★`trains` 는 이미 주석을 걸러 낸 목록이다 — 그것을 쓴다(함정 18: 한 곳에서만).
    if path.name.startswith("run_") and not path.name.endswith("-done.bat"):
        if trains and "--tiny" not in txt \
                and "tool_wandb_push" not in txt:
            warn.append("★**학습 배치인데 `tool_wandb_push.bat` 호출이 없다** — 이 런의 로그는 "
                        "W&B 에 안 올라간다(2026-08-22 사용자 지시). 학습 뒤에 "
                        "`set TL_WB_TAG=<태그>` + `call scripts\\batch\\tool_wandb_push.bat` 를 넣으세요")

    # ── ★★규칙 25 (2026-09-04 신설) — **플래그 화이트리스트 등급**
    #   승인된 제안서 `proposal/done/20260904_배치-파라미터-화이트리스트-approved.md`.
    #   `check_batch_flags` 는 *"파서에 있는가"* 만 본다 — 🚫**파서에 있다고 배치에 써도
    #   되는 것이 아니다.** `--drop-contaminated`(미구현) · `--repeat-kv-reuse`(기각) 등이
    #   지금까지 **아무 게이트도 안 걸렸다.**
    #   ⚠️`scripts/batch/tool_*.bat` 은 **면제**한다 — 스모크는 기각된 축도 **일부러** 돌려
    #   코드 경로를 살려 둔다(`sm_film` 팔).
    if path.name.startswith("run_") and not path.name.startswith("tool_"):
        try:
            from check_flag_whitelist import load as _wl_load
            _wl = _wl_load()
        except Exception:                                    # noqa: BLE001
            _wl = {}
        if _wl:
            _seen = {}
            for _no, _ln in enumerate(lines, 1):
                if _ln.strip().upper().startswith("REM"):
                    continue                                  # ★주석은 명령이 아니다
                for _fl in re.findall(r"(--[a-z0-9][a-z0-9-]*)", _ln):
                    _seen.setdefault(_fl, _no)
            for _fl, _no in sorted(_seen.items()):
                _g, _ev = _wl.get(_fl, ("ok", ""))
                if _g in ("dead", "rejected"):
                    _m = (f"L{_no} 🚫★**`{_fl}` 는 등급 `{_g}` 다** — {_ev}. "
                          f"등급표 `scripts/flag_whitelist.tsv`. "
                          f"다시 열려면 **표의 등급을 먼저 고치고 근거를 적는다**")
                    (warn if path.name.endswith("-done.bat") else err).append(_m)
                elif _g == "exp" and not re.search(r"P\d{3}", txt):
                    warn.append(f"L{_no} ⚠️`{_fl}` 는 실험용(`exp`)인데 배치 어디에도 "
                                f"**계획번호(P0NN)가 없다** — {_ev}")

    # ── ★★규칙 26 (2026-09-04 사용자 지시 13) — **파일명의 계획·단계 = 로그 실험명**
    #   실사고: `run_P085_Stage1_bench_n5000.bat` 안이 `--name P079_review4_expC` 였다.
    #   개명은 파일명만 바꾸고 **안의 로그 이름은 그대로 두기 쉽다** — `check_batch_name` 은
    #   **파일명만** 보고, `runlog` 는 **받은 이름을 그대로** 쓴다. 그 사이가 비어 있었다.
    #   결과: 로그가 `P079_…` 로 남고 `--num 067` 과 겹쳐 **다른 실험군에 들어갔다**.
    #
    #   ★사용자 요구: *"불일치시 claude에게 경고하고 **작업원장에 사유 기입 혹은 배치파일
    #   수정**하도록"* → 면제 경로 둘을 둔다:
    #     (a) 배치 안에 `REM  NAME-MISMATCH: <사유>`
    #     (b) 열린 작업원장에 `실험명 불일치 사유` 와 배치 이름이 같은 줄에
    _mn = re.match(r"^run_(P\d{3,}[A-Za-z]*)_([A-Za-z0-9]+)_", path.name)
    if _mn:
        _plan, _stage = _mn.group(1), _mn.group(2).lower()
        _want = f"{_plan}_{_stage}".lower()
        _names = [n for n in re.findall(r"--name\s+(\S+)", txt)]
        _bad = sorted({n for n in _names if not n.lower().startswith(_want)})
        if _bad:
            # 🚫★2026-09-04 자기교정 — 초판은 **면제 조건이 너무 넓어** 정상 배치를 잡고
            #   결함 배치를 통과시켰다(함정 38: 인쇄와 판정이 갈라진다).
            #   원인 둘: ①`_want` 만 소문자로 안 낮췄다 ②원장 검사가 **배치 이름을 안 봐서**
            #   사용자 지시문에 들어 있는 *'실험명 불일치'* 라는 낱말 하나로 전부 면제됐다.
            #   -> **사유 줄에 배치 이름이 함께 있어야** 면제한다.
            #   ★그리고 **콜론이 붙은 `실험명 불일치 사유:` 형태**만 사유로 인정한다 —
            #   원장에는 사용자 지시 **원문**이 그대로 들어 있고, 그 문장에도
            #   *"실험명 불일치 사유 기입"* 과 배치 이름이 **같은 줄에** 있다.
            #   🚫지시문이 스스로를 면제하면 규칙이 성립하지 않는다.
            _exempt = "NAME-MISMATCH" in txt
            if not _exempt:
                _stem = path.name.replace("-done.bat", ".bat")
                for _w in sorted((ROOT / "handoff").glob("WIP_*.md")):
                    try:
                        _wt = _w.read_text(encoding="utf-8")
                    except OSError:
                        continue
                    for _l in _wt.split(chr(10)):
                        if "실험명 불일치 사유:" in _l and (path.name in _l or _stem in _l):
                            _exempt = True
                            break
                    if _exempt:
                        break
            if not _exempt:
                _m = (f"★**파일명과 로그 실험명이 다르다** — 파일은 `{_plan}` `{_stage}` 인데 "
                      f"`--name {' / '.join(_bad)}` 이다. 로그가 **다른 실험군**으로 들어간다"
                      f"(2026-09-04 실사고: `P085` 배치가 `P079` 로 기록됐다). "
                      f"고치거나, 의도라면 배치에 `REM  NAME-MISMATCH: <사유>` 를 적거나, "
                      f"작업원장에 `실험명 불일치 사유: {path.name} — <사유>` 를 남기세요")
                (warn if path.name.endswith("-done.bat") else err).append(_m)

    # ★2026-08-27 오탐 정정 — 종전에는 **파일 어디에든** RE-RUN 이 있으면 발화했다.
    #   그래서 *"run_P074_stage1 을 먼저 re-run 하라"* 처럼 **다른 배치를 가리키는 문장**에도
    #   걸렸다(2회 오탐). 이 규칙이 잡으려는 것은 *"이 배치가 자기 자신의 재실행"* 인 경우다.
    #   → **다른 `run_*.bat` 이름이 같은 줄에 있으면 그 줄은 세지 않는다.**
    _rr = [ln for ln in txt.splitlines()
           if re.search(r"(?i)\bRE-?RUN\b|재실행", ln)
           and not re.search(r"run_[A-Za-z0-9_]+\.bat", ln.replace(path.name, ""))]
    if path.name.startswith("run_") and _rr:
        names = re.findall(r"--name\s+(\S+)", txt)
        bad = [n for n in names
               if re.search(r"stage\d+(?![a-z])", n, re.I) and not re.search(r"stage\d+[b-z]", n, re.I)]
        if bad:
            warn.append(f"재실행본으로 보이는데 단계명이 그대로다: {sorted(set(bad))} → "
                        f"`stage0b` 처럼 구분되는 이름을 쓰세요. 안 그러면 **같은 날 로그가 "
                        f"이전 측정과 한 파일에 섞인다**(ai_dev_tool/03 §7)")

    # ★★19. **이 `--name` 으로 실행된 로그가 이미 디스크에 있다** (2026-08-14 사용자 지적)
    #
    #   ⚠️**규칙 17 은 배치가 스스로 "RE-RUN" 이라고 선언할 때만 발화한다** — 자기 신고에 의존한다.
    #   2026-08-14 에 `-done` 배치를 **원래 이름으로 되돌려** 재실행하려 했을 때 17 은 조용했다.
    #   되돌리면 *"어떤 실험을 완료했는지"* 가 디스크에서 사라지고 **같은 실험을 두 번 돌리게 된다**
    #   (사용자 지적 · 의사결정함정 D14 · ai_dev_tool/03 §7.1).
    #
    #   → 선언이 아니라 **증거**로 본다: `test_result/` 에 그 `--name` 이 든 로그가 있는가.
    #   경고(에러 아님)인 이유: 로그는 AI 가 개명하고(§8), `-done` 은 사용자가 나중에 붙인다.
    #   **사람이 한 번 보라는 신호**다.
    # ★2026-08-28 — **스모크는 매 세션 같은 이름으로 다시 도는 것이 설계**다.
    #   규칙 19(로그가 이미 있다)와 9d(--name 에 계획번호)가 그것을 실험 재실행으로 오해해
    #   **매 세션 경고 2건**을 냈고, 나는 그것을 매번 넘겼다. 경고를 넘기는 습관이
    #   **진짜 경고까지 죽인다** — 그래서 설계상 예외인 것은 이름으로 면제한다.
    if (path.name.startswith("run_") and "-done" not in path.name
            and path.name not in _RERUN_BY_DESIGN):
        try:
            _logs = [p.name for p in (ROOT / "test_result").glob("*.txt")]
        except Exception:
            _logs = []
        for _nm in sorted(set(re.findall(r"--name\s+([A-Za-z0-9_.-]+)", txt))):
            _hit = [L for L in _logs if _nm in L]
            if _hit:
                _more = f" 외 {len(_hit) - 1}건" if len(_hit) > 1 else ""
                warn.append(
                    f"`--name {_nm}` 으로 실행된 로그가 **이미 있다**({_hit[0]}{_more}). "
                    f"★재실행이면 **단계 구분자를 올리고**(stage0 -> stage0b) `--name` 도 함께 올린다. "
                    f"완료된 것이면 **`-done` 을 붙인다**. "
                    f"🚫**`-done` 을 떼어 원래 이름으로 되돌리지 않는다** (ai_dev_tool/03 §7.1, D14)")

    if re.search(r"(?im)^\s*set\s+TL_OUTDIR\s*=\s*\S", txt):
        if not re.search(r"(?im)^\s*set\s+TL_OUTDIR\s*=\s*$", txt):
            err.append("`TL_OUTDIR` 을 설정하는데 **비우는 줄(`set TL_OUTDIR=`)이 없다** → "
                       "같은 cmd 세션의 뒤 배치로 새어 나가 실험 로그가 스모크 폴더로 간다. "
                       "`setlocal` 만으로는 부족했다(2026-08-13). 종료 경로마다 비울 것")

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
