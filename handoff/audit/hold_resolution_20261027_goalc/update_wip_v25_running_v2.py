"""Persist the running full producer and closed exact review integration."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
 ("1", "작업 내용", "진행: v21검증전량297539SHA/460695위치/462874291IDs와P123212,부분cacheH160219,기존실제채택3421재검토는유지한다. 새독립9/33/추가2 전량저장·새반려0을snapshot37/38 실제0으로회수했다. snapshot36은새TASK bare-ID서식불일치로실제1이며후속plan13/preview도입력없음1로보존했다. 새safeguards3는정확TASK헤더뒤ID만추가허용하고기존잘못된TASK행/부분뷰반려검사를유지해실제0이다. plan15/선택9는actual0:3116원문/미결0/K685E2383X48이며cache채택0이다. 기존18중재와새7중재(새본문3/이전본문4확인)를source/review/bodySHA로고정했다.529487의values역할소실/sumS직접절/고립대괄호를v5에서분리했다. 비프로그램513632틸드구분자·940988원문수학3줄2정확쌍추가registry4와13기존포함3시험실제0,일반code면제0이다. v24영어/명명범위에이어v25는필수내용열전량결손과선택ISBN/비고공란을구분한다. 회귀361(2529f7)/동결재생48(545cb6)/987목적17439-d0d00f 실제0/71.444초(P862E98K27),새종결13·codeUnicodeStyle순서신호0이며개별수정1134427/421191은정확본문선택필수다. 63생산소스preflight886c46/0후전량v25를515030으로시작했고exec세션46878이진행중이다. 마지막확인23913/297539·340.6초(E13459K1280P9172X2),전체종료미확인이다. 실본문검산5는95642/ec0a7b실제0/24.101초로3068본문+48텍스트판정,오류0·codeUnicode0·메모0,style14/numeric6/call6/link손실10/새link1/어휘636/결손60/필드79다. 전량v22/v23/v24 NOT_RUN·goal미완·추가300M미허가다."),
 ("1", "이어받을 지점", "전량v25 exec46878을write_stdin으로회수하고63생산소스는종료까지수정하지않는다. 완료파일만보고exit0추정금지; 실행/해시/전량보존을별도검산하고v21/이전cache와실제채택변동을계수한다. 본문검산5 실제0의신호를회수해새사실/수치/조건/참고/코드/메모/결손직접참조를검토한다. 선택9=3116/K685E2383X48은캐시미채택이며모든개별판독source를최종자동채택에서제외하고정확새본문을연결한다.63소스정적/의미예외13·기존실패들은보존한다. 추가어휘615등의미판독범위를오류0/의미PASS로바꾸지않으며새반례는source와정확본문으로중재한다. 전량잔여/최종zeroHcache/독립verify/재계측/정본/최종handoff/한국어localcommit 모두미완, P일괄EXCLUDE/계약완화금지다."),
 ("2", "작업 내용", "자기tmp에전량v25시작전CPU1/50–90분/63소스동결·RAM28GB/디스크489GiB와원래범위297539SHA/460695위치를안내했다. 전량중검산5약20초CPU1추가로잠시소유CPU최대2임을별도알리고nice10으로시작했다. GPU/모델/학습0,다른세션전용경로/원장/평가/답/코드/프로세스읽기변경0·공통정본/Gitindex변경0이다. 상대공개12:12커밋종료/새GPU진행만읽었고중단/잠금요청0이다.")
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "전량v25진행세션과새저장본문선택및검산복구지점보존",
        "--approval-ref", "현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가"],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
