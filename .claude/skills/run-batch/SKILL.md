---
name: run-batch
description: Windows 실행 배치파일(`run100m_*.bat`, `run_*.bat`)을 작성·수정·검증하는 스킬. "배치파일 만들어", "bat 작성", "실험용 배치", "이 배치 고쳐", "배치 점검" 같은 요청에 사용한다. 또한 사용자가 명시하지 않더라도 여러 학습 명령을 순서대로 실행할 수단을 만들거나 기존 .bat 을 손보려 하면 이 스킬을 적용한다. 순수 ASCII 강제, `<>|%`·chcp 금지, errorlevel 정책(선행 의존만 중단), 태그 위생, 판정 안내문 포함을 검사하고 `scripts/lint_bat.py` 로 기계 검증한다. 인코딩 사고와 "한 런 실패로 배치 전체 중단"을 차단한다.
---

# run-batch

## 왜 이 스킬이 필요한가

`.bat` 은 이 프로젝트에서 GPU 시간을 태우는 유일한 실행 경로인데, 조용히 실패하는 방식이 많다.

- **인코딩**: 한글이 들어가면 cmd 기본 코드페이지에서 깨져 명령이 망가진다. `chcp` 로 덮으면
  파이썬 출력이 또 깨진다. → **순수 ASCII 만.**
- **리다이렉션**: `REM ... -> foo` 처럼 `>` 를 쓰면 cmd 가 리다이렉션으로 파싱할 수 있어
  엉뚱한 파일이 생긴다. `echo` 에서는 `^>` `^<` `^|` 로 escape 해야 한다.
- **`goto ERROR`**: 결과 007에서 [3/4] OOM 이 [4/4]를 죽여 사용자가 수동 재실행해야 했다.
- **태그 누락**: 태그를 안 붙이면 정본 `dense`/`tied` 로그·체크포인트를 **조용히 덮어쓴다**.

## 규칙

### 1. 인코딩·문자 (위반 시 작성 거부)

- **순수 ASCII.** 주석·echo 전부 영문. 한글 설명이 필요하면 계획서(`test_plan/`)에 쓴다.
- `chcp` 금지.
- `<` `>` `|` `%` 금지. 꼭 필요하면 `echo` 안에서 `^<` `^>` `^|` 로 escape.
  주석에서는 그냥 다른 말로 바꿔라(`->` → `to`, `>1.2x` → `over 1.2x`, `<=` → `at most`).
- 줄 끝은 CRLF 여도 되고 LF 여도 cmd 는 실행한다(굳이 변환하지 않는다).

### 2. errorlevel 정책

```
REM 선행 의존이 있는 단계(prepare, 교사/부모 학습)만 중단
python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto ERROR

REM 독립 런은 경고만 하고 계속
python run100m.py train ... --tag X
if errorlevel 1 echo [WARN] X failed - continuing
```

판단 기준: **이 런이 실패하면 다음 런이 무의미해지는가?**
- 예 → `goto ERROR` (prepare, 그 예산의 dense/교사)
- 아니오 → `echo [WARN] ... - continuing` (스윕의 각 변형, 벤치의 각 조건)

### 3. 태그 위생

- 스윕·벤치의 모든 런에 `--tag` 를 붙인다. 태그 없으면 파일명이 `..._{arch}` 가 되어 **정본을 덮어쓴다.**
- 새 태그는 `exp-preflight` 로 충돌 확인 후 `docs/EXPERIMENT_BASELINES.md` §2.6 에 등재.
- 교사·부모를 태그된 것에서 가져와야 하면 `--kd-teacher-tag` / `--init-from-tag` 를 잊지 않는다.

### 4. 명령줄 표준

- `--micro-bs 8 --accum 16 --seq 1024`(유효배치 131K)를 **명시**한다. `--accum` 기본은 8 이다.
- 풀은 `--pool-tokens {2배} --exact-cache`.
- `--compile` 은 mode=default. **커널(`--ternary-kernel*`)과 병용 금지**(코드가 SystemExit).
- VRAM: dense 는 `--no-ckpt` 가능(13.5GB). **tied+KD+dense교사에는 붙이지 않는다**(OOM 위험).

### 5. 배치 안에 반드시 들어갈 문서

헤더 주석:
- 이 배치가 검증하는 **가설/목적** 한두 줄
- **왜 이 설정인지**(특히 표준을 벗어난 부분과 그 이유)
- **총 예상 비용**(시간, VRAM)
- errorlevel 정책 한 줄

꼬리 `echo` 블록:
- **무엇을 어떤 순서로 읽어야 하는지**
- **판정 규칙**(어떤 값이면 채택/보류/폐기)
- 알려진 함정 경고(예: sparse34 의 compare 메모리를 믿지 말 것)

### 6. 마지막 골격

```
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: <어떤 선행 단계가 실패했는지>
pause
```

`goto ERROR` 를 하나도 쓰지 않았다면 `:ERROR` 블록은 도달하지 않지만 남겨둬도 무해하다.

## 검증 (작성·수정 후 반드시 실행)

```
python scripts/lint_bat.py                 # 전체
python scripts/lint_bat.py run100m_P026.bat
```

린터가 잡는 것: 비ASCII 바이트, `chcp`, escape 안 된 `<>|%`, `--tag` 없는 train 명령,
`--accum` 누락, 모든 학습 런이 `goto ERROR` 인 경우(스윕 위험), `pause`/`exit /b` 누락.

**린터 통과는 "문법이 안전하다"는 뜻이고 "실험이 옳다"는 뜻이 아니다.**
실험설계는 `exp-preflight` 스킬이 따로 본다.

## ★줄끝(CRLF) — 배치를 고친 뒤 반드시

`.gitattributes` 가 `*.bat text eol=crlf` 로 선언하는데 **이 워크플로의 편집 도구는 전부 LF 로 쓴다.**
그래서 배치를 고치면 선언과 작업트리가 어긋나고, git 이 매번 경고하며 재작성한다.
**이 저장소에서 두 번 재발했다.**

```
python scripts/lint_bat.py --fix     # 줄끝만 CRLF 로 교정(내용 불변)
python scripts/lint_bat.py           # E11 로 검출된다
```

`.bat` 을 LF 로 통일하지 않는 이유: cmd.exe 는 **LF-only 배치에서 `goto`/라벨이 드물게 어긋난다.**
우리 배치는 `goto NOTIMPL`·`goto CACHEBAD` 를 실제로 쓴다 — 조용히 틀릴 위험을 지지 않는다.

---

## ★2026-08-13 추가 규칙 두 개 (실사고 기반)

### R13. **콘솔에만 뜨고 로그에 안 남는 `echo` 를 쓰지 않는다**

**사고**: `run_recover_dense_best.bat`(P054)이 cmd 창에 *"정본 dense 를 덮어쓰지 않는다 /
best 를 3.7797 과 비교하라 / 설치는 이 `copy` 명령으로"* 를 전부 찍었는데,
**로그 309줄 어디에도 그 문장이 없다.** `runlog.py` 는 **자기가 실행한 것**만 기록하기 때문이다.

→ 로그를 나중에 읽는 사람(**대개 다음 세션의 AI**)은 **판정 기준을 못 본다.**
   그러면 log-to-result 절차가 배치 원문을 따로 찾아 읽어야 하고, 배치가 `-done` 으로
   지워졌으면 **영영 못 찾는다.**

**규칙**: 실험 배치에서 정보가 담긴 `echo` 는 **전부 `runlog.py --note` 로 쓴다.**

```
REM 나쁨 - 콘솔에만 뜬다
echo  Read: paired delta vs mC_wsd against the -0.075 threshold

REM 좋음 - 로그와 콘솔 **양쪽**에 쓴다
python scripts\runlog.py --name P049_x --note "Read: paired delta vs mC_wsd against -0.075"
```

★**이건 같은 말을 두 번 적는 것이 아니다.** `runlog.py --note` 는 파일에 쓴 뒤
`sys.stdout.write(body)` 로 **콘솔에도 그대로 흘린다.** 1:1 치환이므로 함정 18
("적용 대상을 두 곳에서 정의")에 걸리지 않는다.

**허용**: `echo.`(빈 줄) · 구분선(`====`) · **실패 라벨 블록 안**(자식이 이미 죽은 뒤라
runlog 를 못 태울 수 있다). `lint_bat.py` 규칙 13 이 나머지를 잡는다.

### R14. **`!VAR!` 를 쓰면 파일 앞에 `setlocal enabledelayedexpansion`**

**사고**: `run_cleanup_checkpoints.bat` 이 `if not "!TL_OK!"=="YES" goto CANCEL` 을 썼는데
지연확장이 꺼져 있어 cmd 가 **문자열 `"!TL_OK!"` 와 `"YES"` 를 비교**했다. 항상 불일치 →
**사용자가 YES 를 입력해도 CANCEL 로 갔고 44.5GB 가 안 지워졌다.**

★**이건 부주의가 아니라 구조다.** 이 저장소는 `%` 를 금지하므로 **`!VAR!` 가 유일한 변수
확장 수단**이고, 따라서 `setlocal` 누락은 **반드시 재발한다.** `lint_bat.py` 규칙 14 가 잡는다.
