"""Save active full run and all five unfinished text queues for recovery."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
 ("1", "작업 내용", "진행: 공식부분cacheH160219와실제채택3421재검토,검증v21 P123212를유지한다. 새독립9/33/2 전량저장·반려0을snapshot38/plan15로검산하고선택9 실제9eeb63/0은3116원문/K685E2383X48·미결0·cache미채택이다.18+7정확중재/이전본문4확인·새본문3을고정했고guard4정확비프로그램13쌍3시험1717a8/0은일반면제0이다.361회귀/48동결재생/987목적의v25 preflight886c46/0후63생산파일을동결해전량exec46878이진행중이다. 마지막149204/297539·1746.2초(E91740K16020P41442X2)이며종료미확인이다. 실본문검산5 actual95642/ec0a7b0/24.101초는3068본문+48텍스트판정/오류0·codeUnicode0·메모0이나style14/numeric6/call6/link손실10/새link1/어휘636/결손60/필드79가있어의미완료가아니다. 어휘636중정확같은source/body의기존독립ACCEPT57근거를재사용하고나머지579전량을중립사본·2937뷰로만들어5Luna에배정했다(materialize1ace99/0,views9baac2/0). 각32TASK이며controls115/나머지각116ID,각약875k자·총4376811원문자다. 전원진행중이고historical은TASK5뒤종료해006–032를재개시켰다. 원문7986은LF92개지만마지막비LF행까지93행이며PaperWorks실제말미를빠뜨린초기수용을반려했다. 모든역할에tail/무범위전체diff로이미완료ID의마지막논리줄을추가확인시켰다.32474최초실패명령은요약에서소실돼추정cmd주장을정정했고현재전체2937뷰/원문·후보재구성은별도검산한다. 새579의재위필드·완결문과귀속/불확실성·단위결손·도해직접부중재를계속하며기존실패본은보존한다. v22/v23/v24전량NOT_RUN,goal미완·추가300M미허가."),
 ("1", "이어받을 지점", "전량v25 exec46878을write_stdin으로회수하고63생산파일은종료까지수정하지않는다. 실제0관찰후에만DRAFT_V25_PROCESS_EXIT_V1.json을tool_session46878/process_exit_code0/observation_method ACTUAL_EXIT_ZERO_FROM_WRITE_STDIN/완료artifactSHA로새로쓰고준비된verify_v25_artifacts_v1.py를실행한다(현재구문검사만).579 text큐는root_selected_lexical_counter_v1,5역할각TASK001–032·새txt/md만허용이며아직미완이다. 미완료도새collector/plan에결손행으로남겨옛선택으로우회하지않는다. 다음collector는38을재사용해새cohort와2937뷰·strictTASK·safeguards3를추가하고EOF오판/잘못된표/중간본을보존한다. root선택9의body와새579saved결과가다르면모든freshset/source/body/reviewSHA로정확중재한다. source단위해소를P일괄EXCLUDE로바꾸지않는다. 모든개별판독source를최종자동채택에서제외하고정확본문만연결한다. 전체잔여·최종zeroHcache/독립verify/재계측/정본/최종handoff/한국어localcommit은모두미완이다."),
 ("2", "작업 내용", "자기tmp에전량v25 CPU1/50–90분/63소스동결과본문검산5의잠깐CPU최대2를안내했고24.101초종료후장기CPU1로돌아왔다. 새579전량Luna5지정판독과상대12:56 GPU종료/정본문서·Git정리및간접정적읽기사고를자기공개조정문에기록했다. 상대전용경로는조사하지않았으며정확간접파일수미확인이다. 우리GPU/모델/학습·외부상태/Gitindex/공유정본변경0,타세션잠금/중단요청0이다.")
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "전량실행중상태와579전량판독큐및EOF반례복구",
        "--approval-ref", "현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가"],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
