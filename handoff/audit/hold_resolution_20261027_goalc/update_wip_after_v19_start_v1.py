"""Update only this session's WIP through its compare-and-set CLI."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
require_owner = "01a17740-f435-7243-874c-2b5d58181c4c"
if require_owner not in ledger.read_text(encoding="utf-8"):
    raise ValueError("wrong WIP owner")
updates = [('1', '작업 내용', 'v19전량90166은CPU1/계산1로진행중이며43생산소스를동결한다. 이전v17종료91418/독립34257은실제0이다. v19정책255/fresh35회귀0,714목적탐색12457은실제0/19.047초,preflight4783도실제0으로기존37소스불변과독립종결3정확SHA일치를닫았다. v18전량은NOT_RUN이며독립411438의식/변수결손을v19fresh보호로막았다. 158959는실제자료명때문에빈참고자료삭제의견을철회했다. snapshot25실제0은main276중272정형행회수/4서술형회수보완이며새22와반례4는전행저장이다. 철회미판독3행은근거제외·독립3대조를보존했다. 6030은기술본문미복제EXCLUDE의정확root근거를신설했다. 실제중간캐시HOLD160219·goal미완을유지한다.'), ('1', '이어받을 지점', '90166과draft_proposals_v19.log의실제종료를회수하고43소스/전체샤드/297539SHA·460695위치·462874291IDs를독립검산한다. 그전43소스를고치지않는다. historical main009의4행은새표형review로회수하고반복유형13패킷의실제문맥판독을준비한다. 62929는새본문이기존정확root57에속하므로명시supersession이필요하다. main/새22/반례4의실제본문과철회·실패이력및정상리터럴예외를선택에연결한다. 전량잔여유형처리·실제최종캐시/verify·전체재계측·정본연쇄·핸드오프·한국어로컬커밋은미완이다. zeroHOLD계약완화나PENDING일괄EXCLUDE로종결하지않는다.'), ('2', '작업 내용', '자기tmp에v17/후보계측/새22준비의실제종료와v19전량CPU1/43소스동결·예상20–50분을사전안내하고90166으로실행중이다. 상대06시대Broad5단일GPU와GSM8K직렬큐/8GB감시·평가자료격리안내를읽었다. 상대전용자료/원장/코드/프로세스·Git/index변경·상호잠금요청0을유지한다. 실제종료와다음대형CPU/공유정본/Git전환전에자기tmp로재안내한다.')]
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
            "--reason", "실제 v17 종료와 전량검산, 새 저장 검토 및 철회 근거를 현재 상황판에 반영",
            "--approval-ref", "현재 잔여460695 전량 처리 goal과 첨부 목표의 CPU 구현검사 및 WIP 갱신 허가"]
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "compare-and-set complete")
