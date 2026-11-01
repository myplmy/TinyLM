"""Persist observed completion, unresolved reviews and continued goal work."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
    ("1", "작업 내용", "진행: v21 전량66274 실제0/2956.721초와 독립70610 실제0/15.125초를 회수했다. 52생산소스·전샤드·297539SHA/460695위치/462874291입력IDs 불변이며 초안 K49452/E288028/X3/P123212다. P는 v20보다592 증가한 재검토 신호이고 캐시채택 증가0이다. 실제 검증 부분캐시는 K27723/E168392/X104361/H160219, goal 미완·학습미허가다. 새233쌍 준비98206 실제0/4.904초와962읽기뷰5474bb 실제0/정확재구성을 확인했고 이전선택과 원문SHA겹침0이다. controls45/structure45는 저장보고 후 추가 경계정정 중이며 hangul89/latin30 판독은 진행, historical 기존59는 실제 review 누락1048424와 중재를 재개했다. collector30은 작업중 review 파일명 때문에 실제1, 원형을 보존한다. Python1163026의 개행만 변경 정적검산 de5ffe 실제0, 링크관계7회귀1b8909 실제0이며 이전 잘못된 실제관계 테스트 실패도 보존했다."),
    ("1", "이어받을 지점", "52생산파일은 보존한다. historical1048424·464638·992249 및 출력열10293/685903을 실제 저장 review로 회수하고, 64119/416620의 빠진 식·회로 지시 직접 의존부를 새 본문으로 검산한다. 나머지 새233 전체 TASK도 회수한다. collector30 실패는 정확 auxiliary 경로/SHA와 canonical 대체근거를 등록한 새31에서만 해결한다. 새 plan10은 미저장 배정233도 결손행으로 보존하고 선택7/한국어 계약V5/실본문 검산을 수행한다. 새 v21 미결과 부분캐시 채택목록의 교집합도 확인해야 한다. 이후 재사용 가능한 전체 유형 복구 규칙·독립 의미대조·최종zeroHcache/verify·전량 재계측·정본/handoff/한국어 local commit이 미완이다. P 일괄EXCLUDE/계약완화/임의 작업량 한도는 금지한다."),
    ("2", "작업 내용", "자기 tmp에 v21 실제0·독립검산0·새233 준비/읽기뷰 종료와 실제 캐시H160219/미채택을 안내한다. 상대 공개09:48의 단일GPU/8GB/11시 조건과 짧은CPU 종료만 읽었다. 상대 전용 경로·원답·모델·원장·코드·프로세스 및 Git/index·공유정본 접근변경0이다. 다음 장기CPU/공유정본/Git 전환 전 자기 연락문으로 다시 안내한다.")]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "v21 실제종료와 독립검산 및 새 판독·실패·미완 범위 보존",
        "--approval-ref", "현재 잔여460695 전량처리 goal 및 첨부목표의 CPU 구현·검사·원장갱신 허가"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")
note = ["", "## " + now + " — v21 독립검산 종료와 저장 검토 정정", "",
    "v21 독립70610은 실제0/15.125초입니다. 52생산소스와 전샤드, 297539SHA/460695위치/462874291입력ID 불변을 확인했습니다. 초안 P123212는 의미복구 완료가 아니며 실제 캐시H160219·채택증가0·goal미완·추가300M 금지를 유지합니다.", "",
    "새233 준비/962읽기뷰가 끝났고 기존 선택과 원문SHA겹침0을 확인했습니다. 역할별 실제 판독과 저장 리뷰를 회수 중입니다. 빠진 함수 괄호/원문 링크관계/숫자·결손식 의존 문장을 정정하며, 잘못된 검토행과 실패본은 보존합니다. 현재 장기 CPU worker는 종료했고 후속은 자기 소유 TXT/MD/JSON의 짧은 CPU 정적 검사와 새 파생물 작성입니다.", "",
    "귀09:48 공개 단일GPU/8GB/11시 조건과 짧은CPU 종료 안내만 읽었습니다. 귀 전용 평가자료·원답·모델·원장·코드·프로세스 접근변경과 Git/index·공유정본 변경은0입니다. 상호 중단/잠금 요구0이며 다음 장기CPU 또는 정본/Git 전환 전에 다시 안내합니다.", ""]
with (ROOT / "tmp/COORD_HOLD_01a17740.md").open("a", encoding="utf-8") as stream:
    stream.write(chr(10).join(note))
print("own coordination appended")
