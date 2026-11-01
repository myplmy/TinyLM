"""Persist exact scope and next points while the 52-source CPU worker runs."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
    ("1", "작업 내용", "v20전량36526/독립75060실제0은297539SHA/460695위치/462874291IDs/46source불변이며P122620이다.새v21은52source동결/66274CPU1계산1실행중이다.회귀323/재생40v2/수집보호9실제0,목적732v3실제90667/0(26.283초),독립14중12exact수용/2의미반례를자동P로돌리고preflight e795d9/0을닫았다.snapshot29실제83993/0은1789제안/1344ID이며당시새239중80저장/159대기·새14중11저장/3대기였다.plan9/선택6실제0은2851ID/의도2682/미결169이며낮은옛본문우회를차단했다.v20미결전수profile75320실제0/54.317초는77751SHA/122620위치/진단75942/metadata1809·미배정유형233이다.실cacheH160219/goal미완유지."),
    ("1", "이어받을 지점", "66274/v21log실제종료를회수하고52source/전샤드/297539SHA/460695위치/462874291IDs를독립검산한다.52생산file편집금지.기존4역할은새239전체TASK를계속하고표형review로회수한다.27488/79377/10293/685903의출력열TXT복수지명은새review로고친다.새14는전부끝났으나snapshot29이후최종review를다음수집에반영한다.미배정233의정확원문decode/후보/읽기뷰/역할권한을고정하여기존239완료뒤전달하며빈structure_counter는선행가능하다.새수집/계획/선택/실본문재검산·미결중재·최종zeroHcache/verify·전량재계측·정본/handoff/한국어localcommit은미완이다.P일괄EXCLUDE/계약완화금지."),
    ("2", "작업 내용", "자기tmp에v20실제종료·v21의52file동결/CPU1/40–70분시작과짧은v20JSON추가profile의일시CPU2/I/O를안내했다.상대공개08시GPU직렬/8GB/11시조건을확인하고전용path/원답/모델/원장/code/process/Gitindex공유정본접근변경0이다.profile75320실제0을다음에안내하고장기실행종료뒤다시기록한다.")]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "v21실행/독립반례/실제저장본문선택과미배정전수계수의관측상태보존",
        "--approval-ref", "현재잔여460695전량처리goal과첨부목표의CPU관련구현검사·원장갱신허가"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
