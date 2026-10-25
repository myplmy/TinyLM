#!/usr/bin/env python3
"""Update owned WIP cells exclusively through its canonical writer."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "handoff/WIP_20261022_작업원장.md"
CHANGES = {
    (55, "작업 내용"): "원 Muon을 보존한 NorMuon CPU25와 새 학습52/평가46 회귀를 실제 종료0으로 회수했다. 같은format/초기화/offset/Adam의 두 전체300M을 준비하고 beta2=.95/eps=1e-10을 GPU 전에 봉인했다. 실제 cost/학습은 다음 단계이며 AdaMuon은 미구현이다.",
    (55, "산출물"): "078§17;101§529/532;native_training_profile_v1.json;native_training_f4_v1.json;Stage10aWb/10e0W 원로그",
    (69, "작업 내용"): "새 V3 교사는 자발 STOP으로 실제 외부/producer8·CLOSED_PRODUCTION_PAUSED를 회수했다. batch4 새635그룹/190414입력토큰, 누적입력29671199/지도6808802·75M부족45328801이다. source125/옛닫힌16파일과 새 raw/candidate manifest를 독립 검산했고 강제정리/오류/잔존0·종료후여유14808MiB다. 내용 정답성 미검토와 생산 미완은 유지한다.",
    (69, "산출물"): "101§531;Stage4fsYW 원로그;teacher_capacity_resume_root_closure.json;batch_000004/report.json;정상종결/메모리 원형",
    (69, "이어받을 지점"): "같은 생성 조건·cursor[1,12912]·닫힌5batch를 보존해 새 시간/STOP namespace로 재개한다. 학생 본학습과 GPU를 겹치지 않고 새 지도자료190414를 전수 의미검수/학습완료로 세지 않는다.",
    (88, "작업 내용"): "현재84소스 전체스모크0·기존정적70/0/6과 두 한국어 커밋을 회수했다. 새 source 추가 뒤 정적2오류는 플래그 등급/나침반 메타 누락으로 수리 중이다. 교사635증분을 정상 STOP으로 닫고 같은1439374 EOS 두풀을 완결했다. 같은format Muon/NorMuon 각300M은 CPU52/46회귀와 profile/F4를 봉인했으며 실제 비용 입장을 진행한다. 새 지능 성과는 아직 없다.",
    (88, "산출물"): "handoff/audit/oct26_research;101§523~532;원장85~87;Stage10aWb/10e0W CPU;teacher 종료8;28런처 명령원형/삭제영수증",
    (88, "이어받을 지점"): "새 전수정적 수리 회수 뒤 교사 없는 여유14000MiB를 재확인하고 format+Muon/NorMuon 실제cost8→총괄예산→각2289회/300023808 전체본학습→공식평가/128토큰실답을 수행한다.16시 학습/17시 전체 마감을 지키며 원문Muon은 자동 실행하지 않는다.",
}

def main():
    columns = {"작업 내용": 3, "산출물": 4, "이어받을 지점": 5}
    for (number, field), after in CHANGES.items():
        if re.search(r"[\u3040-\u30ff\u3400-\u9fff\u3001\u3002]", after):
            raise ValueError("authored language")
        rows = [line for line in LEDGER.read_text().splitlines() if line.startswith("| **" + str(number) + "** |")]
        if len(rows) != 1:
            raise ValueError("exact WIP row")
        before = [cell.strip() for cell in rows[0].split("|")[1:-1]][columns[field]]
        subprocess.run([sys.executable, "-B", "-X", "utf8", "scripts/wip.py", "--file", str(LEDGER),
            "--override", "--item", str(number), "--field", field, "--expect-before", before,
            "--set-after", after, "--reason", "26일 실제 닫힌 근거와 실행 전 조건 회수",
            "--approval-ref", "사용자26일17시 주도적 연구 및 VRAM 재확보 후 본학습 착수 지시"],
            cwd=ROOT, check=True)

if __name__ == "__main__":
    main()
