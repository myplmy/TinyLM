"""Register the user's bounded wrap-up without resuming the corpus goal."""
from pathlib import Path
import datetime
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
text = ledger.read_text(encoding='utf-8')
assert '01a17740-f435-7243-874c-2b5d58181c4c' in text
assert not any(line.startswith('| **3** |') for line in text.splitlines())
common = [sys.executable, '-I', '-B', str(ROOT / 'scripts/wip.py'), '--file', str(ledger)]
for args in [
    ['--add', '3', '--directive', '진행중이던 보조작업 2개 및 작업중이던 내용까지만 수행하고, 현재까지 수행한 작업 적절한 한국어 로컬 커밋메시지와 함께 저장.',
     '--resume', '47062와119838의 중단된 두 후속을 마무리하고 최신 판독표 수집과 본문 대조 및 현재 범위 기록을 닫은 뒤 소유 명시 경로만 한국어 로컬 커밋한다.'],
    ['--start', '3', '--note', '목표 전체는 paused를 유지한다. 중단 당시 두 보조작업과 진행 중 수집/본문 감사의 한정 마감 및 현재까지 소유 변경의 로컬 저장만 수행한다.',
     '--resume', '두 저장 결과의 원문 대비 diff/EOF를 확인하고 새 수집/계획/본문 감사, 정적 검사와 커밋 allowlist를 확정한다.']
]:
    result = subprocess.run(common + args, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout, result.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
with (ROOT / 'tmp/COORD_HOLD_01a17740.md').open('a', encoding='utf-8') as stream:
    stream.write(chr(10).join(['', '', '## ' + stamp + ' — 사용자 한정 마감과 로컬 저장 준비', '',
        '사용자가 중단 당시 두 보조작업과 작업 중이던 내용까지만 수행하고 현재까지의 관련 변경을 한국어 로컬 커밋하라고 지시했습니다. 전체 goal은 paused 상태를 유지하고, 두 후속 본문과 최신 수집/감사 및 기록만 닫습니다.',
        '현재 index는 비어 있고 branch는 main입니다. 귀13:52 종료 공지를 재확인했습니다. 이후 명시 소유 코드/문서/작은 감사 근거만 index에 올리며 대량 캐시/원문과 귀 전용 자료/변경은 제외합니다. 실제 index 사용 직전에 다시 알리겠습니다.',
        '모든 검사와 수집은 순차 CPU1이며 GPU/모델/학습은0입니다. 귀 작업 중단/잠금 요청은 없습니다.', '']))
