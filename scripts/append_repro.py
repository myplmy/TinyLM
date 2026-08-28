"""`-done` 배치의 **재현 명령**을 대응 결과문서 부록으로 옮긴다.

★왜 생겼나 (2026-08-28)
    `sync_experiments_tsv.py` 는 `-done` 배치를 지워도 되는지 판정할 때
    **"이 배치의 명령이 결과문서에 남아 있는가"** 를 본다. 남아 있지 않으면 `[보류]` 다 —
    지우는 순간 **어떤 명령으로 그 수를 얻었는지가 소실**되기 때문이다.

    그동안 그 부록을 **손으로** 붙여 왔고(문서에 *"자동 추출"* 이라고 적혀 있으나 **도구는 없었다**),
    그래서 `-done` 9건 중 **8건이 보류**로 쌓였다. 손으로 하는 일은 밀린다. 도구로 옮긴다.

무엇을 하나
    1. `-done` 배치에서 `runlog.py ... -- python ...` 의 **실행 명령만** 뽑는다(`--note` 는 뺀다)
    2. 배치 이름의 `P0NN_stageX` 로 `test_result/` 의 로그를 찾아 **앞 세 자리 = 결과문서 번호**를 얻는다
    3. 그 결과문서에 **`## ★부록 — 재현 명령 정본`** 절이 없으면 붙인다(**있으면 건드리지 않는다**)

    python scripts/append_repro.py            # 보고만
    python scripts/append_repro.py --apply    # 실제로 붙인다
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "test_result"
CMD = re.compile(r"runlog\.py\s+--name\s+\S+\s+--\s+(python\s+.+?)\s*$")
STAGE = re.compile(r"run_(P\d{3})_(stage[0-9A-Za-z]*)", re.I)


def commands(bat: Path) -> list[str]:
    out = []
    for ln in bat.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.lstrip().upper().startswith("REM"):
            continue
        m = CMD.search(ln.strip())
        if m:
            c = m.group(1).strip()
            if c not in out:
                out.append(c)
    return out


def result_doc_for(bat: Path) -> tuple[str | None, Path | None]:
    m = STAGE.search(bat.name)
    if not m:
        return None, None
    plan, stage = m.group(1), m.group(2)
    cand = [p for p in RES.glob("*_log_*.txt")
            if plan in p.name and stage.lower() in p.name.lower()]
    if not cand:
        cand = [p for p in RES.glob("*_log_*.txt") if plan in p.name]
    if not cand:
        return None, None
    num = cand[0].name[:3]
    docs = [p for p in RES.glob(f"{num}_*.md") if "_log_" not in p.name]
    return num, (docs[0] if docs else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 부록을 붙인다")
    a = ap.parse_args()

    print("=" * 96)
    print("  `-done` 배치의 재현 명령 -> 결과문서 부록")
    print("=" * 96)
    todo, skip = [], []
    for bat in sorted(ROOT.glob("run_*-done.bat")):
        num, doc = result_doc_for(bat)
        cmds = commands(bat)
        if doc is None or not cmds:
            skip.append((bat.name, "결과문서 또는 명령을 못 찾았다"))
            continue
        txt = doc.read_text(encoding="utf-8")
        if bat.name in txt:
            skip.append((bat.name, f"이미 {doc.name} 에 있다"))
            continue
        todo.append((bat, doc, cmds, num))

    for bat, doc, cmds, num in todo:
        print(f"\n  ★{bat.name}  ->  {num} {doc.name}   (명령 {len(cmds)}개)")
        for c in cmds[:3]:
            print(f"      {c[:104]}")
        if len(cmds) > 3:
            print(f"      ... 외 {len(cmds) - 3}개")
        if a.apply:
            block = [f"\n---\n",
                     f"\n## ★부록 — 재현 명령 정본 (`{bat.name}` 추출, 2026-08-28)\n",
                     "\n> ★**이 절이 있어야 배치를 지울 수 있다**(`sync_experiments_tsv.py`).\n",
                     "> 명령은 **배치에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.\n",
                     "\n```\n"] + [c + "\n" for c in cmds] + ["```\n"]
            doc.write_text(txt.rstrip() + "".join(block), encoding="utf-8")

    print(f"\n  붙일 것 {len(todo)}건 · 건너뛴 것 {len(skip)}건")
    for n, why in skip:
        print(f"    - {n}: {why}")
    if todo and not a.apply:
        print("\n  [보고만] `--apply` 를 붙이면 실제로 부록을 씁니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
