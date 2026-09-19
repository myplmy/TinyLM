"""`-done` launcher의 **재현 명령**을 대응 결과문서 부록으로 옮긴다.

★왜 생겼나 (2026-08-28)
    `sync_experiments_tsv.py` 는 `-done` launcher를 지워도 되는지 판정할 때
    **"이 launcher의 명령이 결과문서에 남아 있는가"** 를 본다. 남아 있지 않으면 `[보류]` 다 —
    지우는 순간 **어떤 명령으로 그 수를 얻었는지가 소실**되기 때문이다.

    그동안 그 부록을 **손으로** 붙여 왔고(문서에 *"자동 추출"* 이라고 적혀 있으나 **도구는 없었다**),
    그래서 `-done` 9건 중 **8건이 보류**로 쌓였다. 손으로 하는 일은 밀린다. 도구로 옮긴다.

무엇을 하나
    1. `-done` launcher에서 실제 실행 명령만 뽑는다(`--note` 는 뺀다)
    2. launcher 이름의 `P0NN[B]_stageX` 로 `test_result/` 로그를 찾아 결과문서 번호를 얻는다
    3. 해당 명령이 빠졌을 때만 launcher별 재현 부록을 붙인다. 같은 문서의 여러 launcher도 명령별로 판정한다

    python scripts/append_repro.py            # 보고만
    python scripts/append_repro.py --apply    # 실제로 붙인다

🚫★**2026-08-29 결함 수정 — 이 도구가 결과문서 7건을 파괴했다**
    2단 루프(쓰기)가 1단 루프(읽기)가 남긴 지역변수 `txt` 를 그대로 썼다.
    그래서 `todo` 에 든 **모든 문서**가 "1단에서 마지막으로 읽힌 문서의 본문 + 자기 부록"
    으로 덮였다. 파괴 이력:
      · `1c3f87e`(08-28) 059 의 본문이 **014·016·047·051·053·058** 을 덮었다
      · `a01f32f`(08-29) 060 의 본문이 **059** 를 덮었다
    ★**교훈**: 읽기와 쓰기를 다른 루프로 나누면 **쓰기 루프가 자기 입력을 다시 읽어야 한다.**
    ★이제 쓰기 직전에 `doc.read_text()` 를 다시 하고, **크기가 줄면 단언으로 죽는다**(함정 35).
"""
from __future__ import annotations
import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

from sync_experiments_tsv import batch_commands, norm as _norm

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "test_result"
TODAY = _dt.date.today().isoformat()


def result_doc_for(launcher: Path) -> tuple[str | None, Path | None]:
    match = re.search(
        r"run_(P\d{3}[A-Za-z]?)_(.+?)-done\.(?:bat|sh)$",
        launcher.name,
        re.IGNORECASE,
    )
    if match is None:
        return None, None
    plan, stage = match.groups()
    logs = sorted(RES.glob("*_log_*.txt"))
    exact = [
        path for path in logs
        if f"{plan}_{stage}".casefold() in path.name.casefold()
    ]
    candidates = exact or [
        path for path in logs
        if re.search(rf"(?:^|_){re.escape(plan)}(?:_|$)", path.name, re.IGNORECASE)
    ]
    if not candidates:
        return None, None
    numbers = {path.name[:3] for path in candidates}
    if len(numbers) != 1:
        return None, None
    number = next(iter(numbers))
    docs = [path for path in RES.glob(f"{number}_*.md") if "_log_" not in path.name]
    return number, (docs[0] if len(docs) == 1 else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 부록을 붙인다")
    a = ap.parse_args()

    print("=" * 96)
    print("  `-done` launcher의 재현 명령 -> 결과문서 부록")
    print("=" * 96)
    todo, skip = [], []
    for bat in sorted(
        path for path in ROOT.glob("run_*-done.*")
        if path.suffix.lower() in {".bat", ".sh"}
    ):
        num, doc = result_doc_for(bat)
        cmds = batch_commands(bat)
        if doc is None or not cmds:
            skip.append((bat.name, "결과문서 또는 명령을 못 찾았다"))
            continue
        txt = doc.read_text(encoding="utf-8")
        # ★★2026-08-30 결함 수정 (2차) — 종전 조건은 `bat.name in txt` 였다.
        #   🚫**배치 이름을 본문에서 언급만 해도 건너뛰었다.** 결과문서 6건에 배치명을
        #   인용했더니 **여섯 건 전부 조용히 건너뛰어졌는데**, 같은 시각
        #   `sync_experiments_tsv` 는 *"명령이 결과문서에 없다"* 로 **보류**를 찍고 있었다.
        #   → 🚫★**두 도구가 같은 질문에 다른 정의를 쓰고 있었다**(R14 위반).
        #
        #   ★**이제 둘 다 "명령이 문서에 있는가" 를 본다.** 판정 함수는
        #   `sync_experiments_tsv.norm` 과 같은 규약이다 — 그것이 정본이고 여기가 따라간다.
        if all(_norm(c) in _norm(txt) for c in cmds):
            skip.append((bat.name, f"이미 {doc.name} 에 명령이 다 있다"))
            continue
        todo.append((bat, doc, cmds, num))

    for bat, doc, cmds, num in todo:
        print(f"\n  ★{bat.name}  ->  {num} {doc.name}   (명령 {len(cmds)}개)")
        for c in cmds[:3]:
            print(f"      {c[:104]}")
        if len(cmds) > 3:
            print(f"      ... 외 {len(cmds) - 3}개")
        if a.apply:
            # ★2026-08-29 결함 수정 — 여기서 **반드시 다시 읽는다**.
            # 종전 판은 1단 루프가 남긴 `txt` 를 그대로 썼다. 그래서 `todo` 의 모든
            # 문서가 **1단에서 마지막으로 읽힌 문서의 본문**으로 덮였다(결과문서 7건 파괴,
            # 커밋 1c3f87e·a01f32f). 같은 문서에 부록이 둘 붙는 경우도 이 재읽기가 살린다.
            body = doc.read_text(encoding="utf-8")
            if all(_norm(c) in _norm(body) for c in cmds):
                print("      [skip] 이미 명령이 다 있다")
                continue
            block = ["\n\n---\n",
                     f"\n## ★부록 — 재현 명령 정본 (`{bat.name}` 추출, {TODAY})\n",
                     "\n> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).\n",
                     "> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.\n",
                     "\n```\n"] + [c + "\n" for c in cmds] + ["```\n"]
            out = (body.rstrip() + "".join(block)).encode("utf-8")
            assert len(out) > len(body), doc.name      # 함정 35 — 줄어들 수 없다
            doc.write_bytes(out)

    print(f"\n  붙일 것 {len(todo)}건 · 건너뛴 것 {len(skip)}건")
    for n, why in skip:
        print(f"    - {n}: {why}")
    if todo and not a.apply:
        print("\n  [보고만] `--apply` 를 붙이면 실제로 부록을 씁니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
