"""CAS updates for this exact session after observed v20 and verifier exits."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
if "01a17740-f435-7243-874c-2b5d58181c4c" not in ledger.read_text(encoding="utf-8"):
    raise ValueError("wrong WIP owner")
updates = [
    ("1", "작업 내용", "v20전량36526실제0/2478.663초·독립75060실제0/14.226초로46source/297539SHA/460695위치/462874291IDs불변과전샤드를닫았다.초안K49343/E288729/X3/P122620이며실캐시H160219유지다.snapshot28/plan8/선택5와본문검산93553실제0을보존한다.저장본문261신호합집합중239쌍을4기존역할에배정하고22정확기존문맥을연결했다.읽기뷰1508개는단순byte동일판독창이며본문이아니다.보존11/구조23검사실제0,새v21정책전량NOT_RUN.저자865115삭제근사재생성은미복구,32474tmp/뷰부분본문/빈v3사고는4파생물동결·원문후보2pin불변이며전체후보기반v4재작성/검토를회수중이다."),
    ("1", "이어받을 지점", "239쌍의모든지정TXT/MD와원문/후보/SHA/EOF를회수하고미결중재·오삭제·단위결손·인과/반복귀속을조치한다.306600새v3선택과더새로운비표준검토의묵시적옛본문fallback/읽기뷰잘림오채택을새수집기에서차단한다.새v21은실제지역함수괄호보존과정상완전구조만좁게증명하고이전회귀/목적원문쌍독립대조후전체제안한다.잔여유형전량처리·최종zeroHcache/verify·전량재계측·정본연쇄·handoff·한국어localcommit미완.PENDING일괄EXCLUDE나zeroH계약완화금지."),
    ("2", "작업 내용", "자기tmp에v20전량36526/독립75060실제종료와46source불변·P122620초안/실cacheH160219분리를안내했다.상대08시대단일GPU직렬큐/CPU질문경계검산/평가자료학습편입0공개문만읽었다.이쪽의상대전용자료·원답·원장·코드·프로세스접근변경/Gitindex공유정본변경0.장기CPU및정본/Git전환전에자기공개tmp에안내한다.")]
for item, field, after in updates:
    matches = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    if len(matches) != 1:
        raise ValueError("exact WIP row required")
    before = matches[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    args = [sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
            "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
            "--reason", "전량 실행과 독립검산 실제 종료 및 새 문맥 판독/보존 검사 상태 반영",
            "--approval-ref", "현재 잔여460695 전량처리 goal과 첨부목표의 CPU 관련 구현 검사 및 원장 갱신 허가"]
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
