"""Update only this session's WIP through its compare-and-set CLI."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
require_owner = "01a17740-f435-7243-874c-2b5d58181c4c"
if require_owner not in ledger.read_text(encoding="utf-8"):
    raise ValueError("wrong WIP owner")
updates = [('1', '작업 내용', 'v19전량90166은실제0/2230.690초,독립22026도실제0/13.199초다.43생산소스/전체샤드/297539SHA·460695위치·462874291IDs보존과stdout일치를닫았다.초안K49058/E288703/X3/P122931은캐시채택이아니다.새후보계측87820실제0/50.870초는77960SHA중76151본문/1809metadata-only·304유형264패킷이며새16쌍준비47363실제0/15.547초다.main276/새22/반례4/반복13저장행회수,반복13의광고잔존·검수메모혼입·정상분류15값오삭제를각실제새본문으로보완했다.새16은14행저장/2행작성중이다.62929정확supersession과6030제한EXCLUDE근거를저장했다.v20정책269/fresh37회귀실제0이나목적/독립반례/전량은아직NOT_RUN이다.실제중간캐시H160219·goal미완유지.'), ('1', '이어받을 지점', '새16의legacy2저장검토를회수하고collector27실제실행→plan7→root선택4→본문재검산2를닫는다.collector26산출물은있지만원tool종료미관찰을0으로추정하지않는다.명시root62929대체와6030metadata-only제외/641587독립v3를선택에연결한다.정상코드·Unicode·전사·수치·스타일정확예외와새영문UI·검수메모·빈수식·오삭제를실제본문으로중재한다.v20은714기존목적쌍+새16전문원문으로탐색하고새종결의독립대조를닫기전전량실행하지않는다.잔여유형전량처리·최종zeroH캐시/verify·전체재계측·정본연쇄·핸드오프·한국어로컬커밋은미완이다.PENDING일괄EXCLUDE나zeroH계약완화로종결하지않는다.'), ('2', '작업 내용', '자기tmp에v19원실제종료90166/독립22026·후보계측87820·새쌍준비47363의CPU1/순차I/O를기록했다.상대공개MMLU/GSM8K직렬단일GPU·8GB감시·평가자료격리안내를읽었다.상대전용원문/평가자료/원장/코드/프로세스·Git/index변경·상호잠금요청0유지.실제캐시채택·정본/Git전환·다음대형CPU전에자기tmp로재안내한다.')]
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
            "--reason", "실제 v19 종료와 전량 보존 검산, 새 원문 판독 및 실패 정정의 현재 상태 반영",
            "--approval-ref", "현재 잔여460695 전량 처리 goal과 첨부 목표의 CPU 구현검사 및 WIP 갱신 허가"]
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "compare-and-set complete")
