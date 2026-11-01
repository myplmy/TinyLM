"""Update only this session's WIP through its compare-and-set CLI."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
require_owner = "01a17740-f435-7243-874c-2b5d58181c4c"
if require_owner not in ledger.read_text(encoding="utf-8"):
    raise ValueError("wrong WIP owner")
updates = [
    ("1", "작업 내용", "v17전량91418은실제0/1916.710초,독립34257은실제0/11.355초로전체샤드·297539SHA·460695위치·462874291입력ID·37소스불변을검산했다. 초안K51391/E288129/X3/P121172이며실제캐시채택0이다. v17잔여후보48803도실제0/42.745초로76657SHA/121172위치·74848본문/1809metadata-only를계측했다. ROOT_AUTHORED_SELECTIONS_V3는2811선택/중재미결0인초안이며최종semanticPASS아니다. snapshot22는실제0으로1428제안/1241ID,새신호276중64저장/212판독중,중재4/철회3독립대조는전행회수했다. 미판독선기재3행은정확SHA철회필터로근거에서제외했다. 실제중간HOLD160219·goal미완을유지한다."),
    ("1", "이어받을 지점", "새신호276전문검토의나머지를다섯역할로끝내고source별과삭제·정상코드/위키예외·날짜귀속·교차3본문차이를총괄대조한다. 801462최신v4와55367v3등명시정정본을정확SHA로회수하며높은파일버전으로추측선택하지않는다. snapshot20/21의파서실패및22의실제회귀0/철회필터3은보존한다. v17잔여유형의새source쌍과다음정책을준비하고전량복구를계속한다. 실제최종캐시/verify·전체재계측·정본연쇄·핸드오프·한국어로컬커밋은미완이며final zeroHOLD계약완화/일괄제외종결을금지한다."),
    ("2", "작업 내용", "자기tmp에v17전량CPU1사전안내와실제91418/34257종료및후속후보전량계측을기록했다. 후속48803도실제0/42.745초로끝나현재대형CPU는없다. 상대05시MMLU단일GPU/6GiBallocator·증가8GB감시안내를읽었다. 상대전용자료/원장/코드/프로세스·Git/index변경·상호잠금요청0을유지한다. 공유정본/Git및다음원3스트림읽기전에재안내한다."),
]
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
