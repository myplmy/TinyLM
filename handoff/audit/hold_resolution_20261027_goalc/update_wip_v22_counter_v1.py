"""Record partial-cache rechecks and the new negative semantic counter."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
assert "01a17740-f435-7243-874c-2b5d58181c4c" in ledger.read_text(encoding="utf-8")
updates = [
    ("1", "작업 내용", "진행: v21 전량66274/독립70610 실제0의52소스·297539SHA/460695위치/462874291IDs 보존과 P123212는 유지한다. 부분캐시 전2154912위치 ledger 재검산33811 실제0/12.568초로 실제 채택3421(학습3413/검증8)을 재검토 대상으로 구분했다: 새 보수적P2911/다른새후보510이며 결함확정수는 아니다. 공식 부분cacheH160219/goal미완/학습미허가다. snapshot31 실제88358/0은2104제안/1520ID, 새239와14 전량저장, 당시새233은153/80미저장이었다. plan10/선택7 실제0은3084ID/의도2998/미결86이다. 실제본문검산3은97128/0,2950본문/48텍스트판정/메모0/오류0으로 source-call7·link-loss18·code2·style13·numeric7 신호를 찾았다. 합집합46+기계미결2 전체48를 controls/structure 각24에 배정하고 중립사본·311뷰 재구성 실제0을 확인했다. 새233/48의 최신완료 보고는 다음수집32로 검산한다. v22 회귀339 실제0(앞선2실패보존),955목적30762/0/65.145초의 새종결1은 독립146452에서 실제 수식/변수 결손을 발견해 자동미채택/전량v22 NOT_RUN이다. 전수계수21164/0/25.321초는78102SHA/123212위치,본문76293/개별metadata1809,새유형33SHA/60위치이며 채택0이다."),
    ("1", "이어받을 지점", "기존55생산파일과 v22 실패·반례는 보존한다. collect32에 root_selected_literal_counter_v3 48과policy_v22_literal_counter_v1 1을 추가하고뷰/TASK핀·정확auxiliary registry를 유지해 최신233/48/1 저장행·미결·기계반려를 회수한다. Cauchy146452의 첫 명명정의 뒤 빈괄호만 정리하고 수식 직접의존부를 hold한 새본문/표를 회수한다. 실제 비어버린 수학절제목과 채워진 참고/주제값은 구분한다.146452 source의 ‘여기서 은 주어진 계수들이다’, ‘여기서 에 따라’는 새 결손반례다. 새v23/독립재생은 검증v21을 baseline으로 이 결손을 과거종결에도 fresh 검사하고 전량v22는 실행하지 않는다. 넓은 복구유형은 기존empty-section/metadata/구조함수 재사용과 독립대조 후 전량처리한다. plan11/선택8은 새코호트 전량배정 결손과 서로다른새본문·기존exactroot 충돌을 숨기지 않는다.1257055/166766/233893/293331 실제차이와7383/526859 새검토를 명시중재하고 실본문검산·모든새실패를 검산한다. 전량잔여/최종zeroHcache/verify/재계측/정본/handoff/한국어localcommit 미완, P일괄EXCLUDE/계약완화금지."),
    ("2", "작업 내용", "자기tmp에 v21검산종료,부분캐시실제3421재검토,955목적종료,78102SHA후보 전수계수의CPU1/1–3분 안내를 남겼다.30762와21164는 실제0으로 종료했고 모델/GPU/원토큰스트림을 이 두 검사에서 새로 열지 않았다. 상대공개 GPU전부종료/자기문서폐합만 읽었고 전용평가자료·원답·모델·코드·원장·프로세스 접근변경0,공통실험정본/Gitindex변경0이다. 자기WIP만CAS로 현재 실제상태를 갱신한다. 다음 장기CPU/공통정본/Git전환 전 자기연락문에 사전안내한다.")
]
for item, field, after in updates:
    rows = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("| **" + item + "** |")]
    assert len(rows) == 1
    before = rows[0].split("|")[{"작업 내용": 4, "이어받을 지점": 6}[field]].strip()
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--override", "--file", str(ledger),
        "--item", item, "--field", field, "--expect-before", before, "--set-after", after,
        "--reason", "부분캐시 실제 재검토와 새 의미반례 및 전수진단 종료 보존",
        "--approval-ref", "현재 잔여460695 전량처리 goal 및 첨부목표 CPU·코드시험·문서갱신 허가"],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(item, field, "CAS complete")
