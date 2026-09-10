#!/usr/bin/env python3
"""★★PreToolUse 훅 — **저장소에 쓰면서 백슬래시를 넣는 셸 명령을 막는다**.

## 왜 있나 (2026-09-08(3차) 사용자 지시 2E — 제안서 승인)

`ai_dev_tool/01` 의 백슬래시 사고가 **누적 16회**다. 규약은 이미 **세 곳**에 있다
(`CLAUDE.md` · `ai_dev_tool/06` · 세션 시작 프롬프트). ★**네 번째 사본이 세 번째보다
잘 들을 이유가 없다**(규칙 42) — 그래서 텍스트가 아니라 기계로 막는다.

## 무엇을 막나 — **두 조건이 동시에 참일 때만**

1. **쓰기 의도**가 있다: heredoc(`<<`) · 파일 리다이렉트(`>`/`>>`) · `tee` · `sed -i` ·
   `Set-Content`/`Out-File`/`Add-Content`
2. 명령 본문에 **재해석되는 이스케이프**가 있다: `\\n \\t \\b \\r \\f \\v \\0 \\x \\u \\\\`

🚫**둘 중 하나만이면 통과**시킨다. 읽기 전용 정규식(`grep '\\d+'`)도, 역슬래시 없는
heredoc 도 막지 않는다.

## 사고의 실제 모양 (이 훅이 잡았어야 하는 것)

    python - <<'PY'
    s = "...print(f\\"\\\\n  ...\\")"      # ← 이 `\\\\n` 이 **실제 개행**이 됐다
    io.open(p,"w").write(s)
    PY

**2026-09-08(3차)에 실제로 났다** — `scripts/diag_lrm_values.py` 가 구문 오류가 됐고
`check_imports` 가 잡았다. ⚠️**게이트 35(제어문자)는 개행을 제어문자로 세지 않아 못 잡는다.**

## 예외

`backslash_whitelist.tsv` 가 정본이다. **면제를 추가할 때는 실제로 막힌 정당한 명령을 적는다.**
명시적 예외 토큰은 `ALLOW_BACKSLASH_WRITE` — 훅이 **크게 인쇄하고** 통과시킨다.

## 규약

- 종료코드 **2** = 차단(stderr 가 모델에게 보인다) · **0** = 통과.
- 🚫**판단이 안 서면 통과시킨다.** 훅이 죽어서 작업을 막는 것이 사고보다 나쁘다
  (함정 44 — 감시 도구가 감시 대상을 막으면 안 된다).
"""
import io
import json
import os
import re
import sys

# ★★Windows cp949 대응 — 훅은 **호스트 콘솔 인코딩**으로 stderr 를 쓴다.
#   🚫안 고치면 차단 메시지가 통째로 깨져 **왜 막혔는지 못 읽는다**(첫 실행에서 실제로 그랬다).
#   ★환경변수(`set PYTHONIOENCODING=utf-8`)에 의존하지 않는다 — 훅은 우리가 부르는 게 아니다.
for _s in ("stdin", "stdout", "stderr"):
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
WL = os.path.join(HERE, "backslash_whitelist.tsv")

# ★재해석되는 이스케이프만 본다. `\/` `\-` 같은 무해한 것은 안 본다.
#   🚫**`\\` 를 문자군에 넣지 않는다** — 넣으면 `\|`(마크다운 표의 이스케이프된 파이프)를
#   파이썬 문자열에 담은 `"\\|"` 가 걸려 **정당한 명령이 막힌다**(실물 오탐 1건에서 확인).
#   ✅빼도 `\\n`·`\\t` 는 여전히 잡힌다 — 두 번째 백슬래시가 `n`·`t` 와 짝을 이룬다.
BAD = re.compile(r"\\[ntbrfv0xu]")

WRITE = (
    re.compile(r"<<-?\s*['\"]?\w"),          # heredoc
    # 파일 리다이렉트. 🚫`(?<![0-9\s])` 로 쓰면 **공백 뒤의 `> 파일` 을 놓친다**
    #   (`echo "a\nb" > handoff/x.md` 가 실물 미탐 1건이었다). 숫자만 배제한다 —
    #   `2>&1`·`>/dev/null` 은 `NOT_WRITE` 가 먼저 지운다.
    re.compile(r"(?<![0-9])>>?\s*[^\s&|]"),
    re.compile(r"\btee\b"),
    re.compile(r"\bsed\b[^|]*\s-i\b"),
    re.compile(r"\b(Set-Content|Out-File|Add-Content)\b"),
)
# 쓰기로 보지 않는 리다이렉트
NOT_WRITE = re.compile(r">\s*(/dev/null|\$null|NUL)\b|2>&1")


def load_wl():
    ro, path, tool, esc = [], [], [], []
    try:
        for ln in io.open(WL, encoding="utf-8").read().split("\n"):
            if not ln.strip() or ln.lstrip().startswith("#"):
                continue
            c = ln.split("\t")
            if len(c) < 2:
                continue
            kind, pat = c[0].strip(), c[1]
            {"readonly": ro, "path": path, "tool": tool, "escape": esc}.get(kind, []).append(pat)
    except Exception:
        pass
    return ro, path, tool, esc


def verdict(cmd):
    """(차단할까, 사유) 를 돌려준다."""
    ro, paths, tools, escs = load_wl()
    for e in escs:
        if e and e in cmd:
            return False, "escape:" + e
    if not BAD.search(cmd):
        return False, "백슬래시 이스케이프 없음"
    # 쓰기 의도
    probe = NOT_WRITE.sub(" ", cmd)
    if not any(p.search(probe) for p in WRITE):
        return False, "쓰기 의도 없음"
    # 화이트리스트 — 경로(저장소 밖)
    #   ★슬래시 방향을 맞춘 뒤 본다. 🚫안 맞추면 `C:/.../Temp/claude/` 를 못 알아본다(실물 오탐 1건).
    flat = cmd.replace(chr(92), "/")
    for p in paths:
        if p and p.replace(chr(92), "/") in flat:
            return False, "path:" + p
    # 화이트리스트 — 도구 실행
    for t in tools:
        if t and t.replace(chr(92), "/") in flat:
            return False, "tool:" + t
    # 🚫**읽기 전용 목록은 여기서 안 본다.** 쓰기 의도가 이미 확인됐기 때문이다 —
    #   `echo "a\nb" > handoff/x.md` 를 `echo` 로 통과시키면 **미탐**이다(실물 1건에서 확인).
    #   ★TSV 의 `readonly` 행은 *"쓰기 의도 판정이 이것들을 왜 안 잡는가"* 의 문서이지 우회로가 아니다.
    _ = ro
    return True, "저장소 쓰기 + 재해석되는 백슬래시"


MSG = """
============================================================
🚫★★ 백슬래시 훅 — 이 명령을 막았다 (사유: {why})

  저장소 파일에 **쓰면서** 재해석되는 백슬래시({hits})가 들어 있다.
  ★이 조합이 이 저장소에서 **누적 16회** 사고를 냈다 —
    `\\b`·`\\t` 가 실제 제어문자가 되거나 `\\n` 이 실제 개행이 되어
    **문법적으로 멀쩡한 쓰레기**가 저장됐다.

  ✅**이렇게 한다**: `Write` 또는 `Edit` 툴로 그 파일을 쓴다.
     그 둘은 셸을 거치지 않으므로 백슬래시가 그대로 저장된다.

  ⚠️정말 셸로 써야 하면 명령에 `ALLOW_BACKSLASH_WRITE` 를 넣는다(훅이 통과시키고 기록한다).
     🚫습관으로 붙이지 않는다 — 붙일 때마다 **왜 Write 툴이 안 되는지** 한 줄로 답할 수 있어야 한다.
  ★면제가 필요한 정당한 형태면 `.claude/hooks/backslash_whitelist.tsv` 에 실물 명령과 함께 적는다.
============================================================
"""


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0                       # 🚫판단이 안 서면 통과
    tool = data.get("tool_name") or data.get("tool") or ""
    if tool not in ("Bash", "PowerShell"):
        return 0
    ti = data.get("tool_input") or data.get("input") or {}
    cmd = ti.get("command") if isinstance(ti, dict) else None
    if not isinstance(cmd, str) or not cmd:
        return 0
    block, why = verdict(cmd)
    if not block:
        if why.startswith("escape:"):
            print("⚠️★백슬래시 훅 — 명시적 예외로 통과시켰다(" + why + "). "
                  "🚫습관이 되면 훅이 없는 것과 같다.", file=sys.stderr)
        return 0
    hits = " ".join(sorted(set(BAD.findall(cmd))))
    sys.stderr.write(MSG.format(why=why, hits=hits or "?"))
    return 2


if __name__ == "__main__":
    sys.exit(main())
