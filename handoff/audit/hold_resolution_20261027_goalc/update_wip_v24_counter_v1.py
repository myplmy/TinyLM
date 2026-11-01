"""Record observed saved-body integration and semantic rejections honestly."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
 ("1", "작업 내용", "진행: 검증v21 전량297539SHA/460695위치/462874291IDs 및 P123212를 보존한다. 실제 부분cacheH160219와 기존채택3421(학습3413/검증8)의 새검토 필요는 변함없다. collect34/35와 plan11/12 실제0:3084ID, 새239/14/233/48/1 전량저장·미저장0·새기계반려0이다. 기존25실패와 모든실패본은 보존했다. root18개별중재와 exact전임2건supersession을 고정한 선택8 실제0은3084ID/미결0이며 cache채택0이다. 59479의 단위없는1.4파편·940988의 잘못된중간등식복구를 거부했고26368등의새개별판독은별도다. 실본문검산4 실제75037/0/20.468초는3036본문+48텍스트판정,메모0/오류0,신호합집합37·call6/link손실10/새link1/code2/style14/numeric6/어휘615/결손61/필드80이다. 이 신호는오류확정이아니며 새2(1239923/529487) 독립수정은저장보고수신·수집전이다. v23 회귀351/재생43/955목적 실제0/74.561초:새종결9는독립9전량저장(8ACCEPT/1REVISE). 구조전수33정확원문 재생93575/0/3.569초·101뷰재구성 실제0, 자동E11/K4/P18 중실제수식결손반례가발견돼 전량v22/v23 NOT_RUN이다. 새v24는명명정의첫문장밖내용을자동정상화하지않으며영어역할결손도검사한다.356회귀839cd4/0와47재생485a99/0,987합집합목적57756/0/71.530초(P861/E99/K27)이다. v24초기부분격리2실패는수정전소스와로그를보존했다. 새종결14중897170의언어열전량결손은독립중재로일반공란판정을반려했다. 최종캐시/전량재계측/정본/커밋미완·추가300M미허가."),
 ("1", "이어받을 지점", "v21/기존61생산소스와v22/v23/v24실패·반례를보존한다. 구조33 전체의최신저장행과9/2를새collector로회수하고 unknown파일/배정/TASK/뷰/보조registry검사를유지한다. 897170은부양어열전량결손·비교예고를hold하고실제어근-PMP6쌍만보존하며467565는모형조건/기호/표현결손응용표전체를exacthold한다. source혼입기호를만들지않는다. 새v25에서전열공란인필수내용축을비고/ISBN같은선택metadata와구분해P로유지하고987+구조33purpose/회귀/독립대조뒤전량은검증v21기준으로한번수행한다. 자동종결의알려진의미반례를숨기거나P일괄EXCLUDE/zeroH계약완화금지. 선택8의18중재는새코호트에자동전파하지말고새9/33/2를포함한전체freshset충돌을명시중재한다. 513632의틸드readercomment비코드 exactpair와940988의수학직접격리2건은일반code면제와분리해검증해야한다. 실제body정책신호61/필드80·추가어휘615는처리검토대상이지의미PASS가아니다. 전량잔여·최종zeroHcache/독립verify/재계측/정본/handoff/한국어localcommit 미완이다."),
 ("2", "작업 내용", "자기tmp에v22전수계수25.321초종료·v23목적CPU1안내를남겼고상대공개12:12커밋종료/새FalconGPU진행만읽었다. 전용모델/원답/평가자료/코드/원장/프로세스접근변경0·공통실험정본/Gitindex변경0이다. 자기CPU의v23/v24목적955/987과구조33source디코드3.569초는종료했고GPU/모델/학습0이다. 선택8과WIP만자기경로에저장했고새전체sourceCPU실행전소유연락문에조건·시간·자원을안내한다.")
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "저장본문18중재와독립의미반례및새목적실제종료",
        "--approval-ref", "현재잔여460695전량정제goal및첨부목표CPU코드시험문서허가"],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
