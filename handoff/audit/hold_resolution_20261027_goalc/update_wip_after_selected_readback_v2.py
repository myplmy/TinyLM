"""Update only this session's WIP through its compare-and-set CLI."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
require_owner = "01a17740-f435-7243-874c-2b5d58181c4c"
if require_owner not in ledger.read_text(encoding="utf-8"):
    raise ValueError("wrong WIP owner")
updates = [('1', '작업 내용', 'v20전량36526은CPU1/계산1로진행중이며46생산파일동결이다.v19실제90166/0·독립22026/0·후보계측87820/0·새16준비47363/0을보존한다.v20정책269/fresh37·732목적42840/0·독립3준비16362/0·preflight61005/0은실제종료다.snapshot28실제0은1698제안/1333ID이며main276/새22/반례4/반복13/새16(14원배정+2재배정)/새독립3을회수했다.선택4는입력참조오결합으로실제1을보존했고24정반례검사0후plan8/선택5실제0으로2850SHA/2850ID선택의도를닫았다.본문검산93553/0은2803본문/47문자판정·메모혼입0이나code2/style15/수치6/어휘559/결손56/field69/wiki50진단이남는다.실제cacheH160219·goal미완유지.'), ('1', '이어받을 지점', '36526과v20log의실제종료를회수하고46sources/전체shards/297539SHA·460695위치·462874291IDs를독립검산한다.그전46source를고치지않는다.본문진단v2의정상literal예외와실제결손/의미변경을source/body/review정확SHA로구분해조치한다.legacy역할의865115자기초안삭제→근사재생성/24219자기초안덮기를보고받아본문권한을닫고현5파생물freeze/원문후보4pin불변확인/다른역할재도출2를회수했다.삭제전bytes는미회수이며전체역사보존/정확복구라하지않는다.옛ACCEPT4입력명오독은27/선택4실패를보존하고28/선택5로고쳤다.잔여유형전량처리·실제최종zeroHcache/verify·전량재계측·정본연쇄·handoff·한국어localcommit은미완.PENDING일괄EXCLUDE나zeroH계약완화로종결하지않는다.'), ('2', '작업 내용', '자기tmp에v19전량/검산/후보계측/새16준비실제종료와v20CPU1/46file동결/20–50분·짧은저장본문검산병행CPU/I/O를안내했다.상대공개문의범위밖계획reader사고/수집필터보완과GPU직렬큐안내를읽고중단/lock/문서수정을요구하지않는다.이쪽의상대전용자료/원답/원장/코드/프로세스접근변경·Git/index변경0유지.공유정본/Git전환은사전에자기tmp에안내한다.')]
for item, field, after in updates:
    matches = [line for line in ledger.read_text(encoding="utf-8").splitlines()
               if line.startswith("| **" + item + "** |")]
    if len(matches) != 1:
        raise ValueError("exact item row missing")
    index = {"작업 내용": 4, "이어받을 지점": 6}[field]
    before = matches[0].split("|")[index].strip()
    args = [sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override",
            "--file", str(ledger), "--item", item, "--field", field,
            "--expect-before", before, "--set-after", after,
            "--reason", "v20 실행과 실제 원문 선택 검산, 저자 경계 위반 및 별도 재배정 증거 반영",
            "--approval-ref", "현재 잔여460695 전량 처리 goal과 첨부 목표의 CPU 구현검사 및 WIP 갱신 허가"]
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "compare-and-set complete")
