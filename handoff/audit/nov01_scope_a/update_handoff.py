"""Narrow approval/state synchronization; WIP is strictly read-only here."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
WIP = ROOT / 'handoff/WIP_20261022_작업원장.md'
HANDOFF = ROOT / 'handoff/202611011123_HANDOFF.md'
OLD_PROPOSAL = '20261101_정제세션-격리와-공용검사-범위-명시-제안서.md'
NEW_PROPOSAL = OLD_PROPOSAL[:-3] + '-approved-on-going.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rows(text, wip=False):
    out = {}
    for line in text.splitlines():
        cells = line.split(' | ')
        if len(cells) != 6 or not line.startswith('| '):
            continue
        key = cells[0].removeprefix('| ').strip('*')
        if key.isdigit():
            out[key] = cells
    return out


def main():
    phase = sys.argv[1]
    if phase not in ('prepare', 'close'):
        raise ValueError('one explicit synchronization phase required')
    receipt = BASE / ('HANDOFF_SYNC_' + phase + '.json')
    if receipt.exists():
        raise FileExistsError('synchronization receipt already exists')
    wip_sha = sha(WIP)
    board = rows(WIP.read_text(), True)
    if len(board) != 106 or '106' not in board:
        raise ValueError('exact current WIP106 required')
    text = HANDOFF.read_text()
    before = sha(HANDOFF)
    old = rows(text)
    if any(old[key][1] != board[key][1] for key in old):
        raise ValueError('historical directive mismatch; do not rewrite original instructions')
    current = board['106']
    entry = ('| 106 | ' + current[1] + ' | 승인 A의 입력 범위와 기본 검사 보존 | '
             '명시 collector·판독 거부·자식 전달·CPU 회귀·로컬 커밋·11월1일 상세 보고 | '
             + current[3] + ' | ' + current[2] + ' — ' + current[4] + ' |')
    lines = text.splitlines()
    if '106' in old:
        lines = [entry if line.startswith('| 106 | ') else line for line in lines]
    else:
        at = next(i for i, line in enumerate(lines) if line.startswith('| 105 | '))
        lines.insert(at + 1, entry)
    text = chr(10).join(lines) + chr(10)
    text = text.replace(OLD_PROPOSAL, NEW_PROPOSAL)
    replacements = {
        '세션01a0b33b-d14e-7c40-ada8-229a1f97eabd, 105건. 51·105는 완료, 전체 원장은 미완이다.':
            '세션01a0b33b-d14e-7c40-ada8-229a1f97eabd, 106건. 51·105는 완료이며106 상태는 아래 원문 표를 따른다. 전체 원장은 미완이다.',
        '[오후 결과보고](../docs/research/20261101_오후_독립연구_결과보고.md)':
            '[최종 결과보고](../docs/research/20261101_자율주도_연구_최종보고.md)',
        '별도 원장09·환경파일·공유 검사기·정제 전용 코드와 flag는 수정하지 않았다.':
            '별도 원장09·환경파일·정제 전용 코드와 dirty flag는 수정하지 않았다. 사용자106 승인 후 중앙 collector·공용 static/smoke의 opt-in 배선만 수정했다.',
        '|WIP·현재 인계|필요|51/105완료·46막힘·59미완·원문105 보존|전체 원장은 미마감|':
            '|WIP·현재 인계|필요|51/105완료·106 추가·46막힘·59미완·원문106 보존|전체 원장은 미마감|',
        '|공유 검사기/환경|이번에는 수정 안 함|diff0|R58의 추가 구현 승인 제안|':
            '|공유 검사기/환경|사용자106 A 승인 반영|명시 입력·read guard·자식 영수증, 기본 USER_GLOBAL 유지|새 전체 smoke는 별도 미실행|',
        '공용 검사 범위 변경은 아래 A안 승인 전 실행하지 않으며 KoBEST 추가 의존성도 미승인이다.':
            '공용 검사 A 구현과 CPU 검증은 사용자106 승인으로 수행했다. 새 전체 smoke와 KoBEST 추가 의존성 설치는 아직 미승인이다.',
        '공유 검사 A안·KoBEST는 별도 승인/설치·원천 선결을 닫아야 새 실행을 편성한다.':
            'A의 CPU 구현은 사용자106 승인으로 회수했고, 전체 smoke의 새 실행창·KoBEST 설치·원천 선결을 닫아야 새 실행을 편성한다.',
        '|그 외|[공유 검사 A/B/C 제안](../proposal/' + NEW_PROPOSAL + ')|Codex00 R58은 작업흐름 생성기/검사기 변경의 직접 지시/승인을 요구|권장 A의 명시 collector/read guard 구현 범위를 승인할지 결정|A 승인 또는 대안 지정|기준·사용자 전역 기본을 보존하고 자식 판독 회귀 후 새 전체 smoke|':
            '|그 외|[승인 A 구현](../docs/research/20261101_A_검사입력범위_구현계약.md)|사용자106이 A·CPU·로컬 커밋만 승인|새 전체 smoke는 후속 허가창에서 실행|현재 추가 GPU 요청 없음|기준·USER_GLOBAL 기본 보존, 현 전체는 NOT_RUN|',
        '정확 WIP는 handoff/WIP_20261022_작업원장.md·동일세션01a0b33b-d14e-7c40-ada8-229a1f97eabd·105건이다.51/105완료,':
            '정확 WIP는 handoff/WIP_20261022_작업원장.md·동일세션01a0b33b-d14e-7c40-ada8-229a1f97eabd·106건이다.51/105완료·106은 승인 A 구현과 CPU·커밋·보고,',
        '원형기준/사용자기본유지A안추가승인전공유하네스를바꾸지않는다.':
            '사용자106 승인 A는 구현·CPU 검증을 했으며 사용자 기본/원형 기준을 유지한다. 새 GPU·전체 smoke는 실행하지 않는다.',
        '공유 collector/read guard A 승인 후 재실행': '승인 A의 명시 입력 구현·CPU 검증 후 새 실행창에서 범위를 확정',
        '사용자 R58 구현 승인|': '사용자106 구현 승인 반영·새 범위 실행은 후속|',
        '사용자 collector 승인·유효 CPU/GPU 시간|': 'collector 구현 승인 완료·유효 CPU/GPU 시간은 후속|',
        '공유 collector 승인 후 새 전체 실행': '승인 A의 CPU 검증 후 새 허가창에서 전체 실행',
        '원형 기준을 유지하는 A안 승인 후 새 실행': '승인 A의 CPU 검증은 완료, 원형 기준을 유지한 새 허가창의 전체 실행 필요',
        '공유 검사 무단 변경.': 'A 범위 밖 공유 검사 변경·새 GPU/모델/전체 smoke.',
        '최초 인계 원문105건을 보존하며 오후 결과와 다음 승인 선결을 반영한다.':
            '최초 원문105건과 사용자106을 보존하며 승인 A·CPU 결과와 후속 선결을 반영한다.',
        '정확WIP105건·COMPASS·EXPERIMENT_BASELINES': '정확WIP106건·COMPASS·EXPERIMENT_BASELINES',
    }
    for old_text, new_text in replacements.items():
        text = text.replace(old_text, new_text)
    stamp = datetime.now().astimezone().isoformat()
    out = []
    for line in text.splitlines():
        if line.startswith('- **최종 갱신**:'):
            line = '- **최종 갱신**: ' + stamp + '. 최초11:23 스냅샷은2928507b에 보존했다. 같은 인계의 승인 A 후속 갱신이다.'
        elif line.startswith('- **정적 감사 기록**:'):
            line = '- **정적 감사 기록**: [정적 감사 기록](audit/nov01_afternoon/PRODUCT_BOUNDARY_STATIC_AUDIT.json)은 옛69PASS/2ERROR/6NOT_RUN이다. 승인 A의 [명시 입력 검사](audit/nov01_scope_a/OWNED_STATIC_v5.json)는 별도 범위이며 전역 PASS가 아니다. 현재 전체 smoke는 NOT_RUN이다.'
        out.append(line)
    text = chr(10).join(out) + chr(10)
    marker = '### 2.4 사용자106 승인 A의 후속'
    if marker not in text:
        note = (marker + chr(10)*2 +
                'USER_GLOBAL 기본과 원래 판정식을 유지하고 manifest+SHA를 준 경우만 OWN_SCOPED를 사용한다. '
                '명시160입력의 여섯 원형 검사는6PASS/0ERROR/71NOT_RUN이었고 제외 canary·소유 결함·자식/손자·누락 영수증을 CPU에서 검증했다. '
                '검사기 판독과 무결성 판독을 별도로 기록한다. Python audit은 OS sandbox가 아니며 native/shell 자식은 거부한다. '
                '최종 문서 포함 범위와 원로그는 [A 감사](audit/nov01_scope_a/OWNED_STATIC_v3.json)를 따른다. '
                '15시 이후 GPU·모델·전체 smoke는0이며 현재 전역 PASS나 새 지능 성과를 주장하지 않는다.' + chr(10)*2)
        text = text.replace('## 3. 변경 파일과 정본', note + '## 3. 변경 파일과 정본')
    HANDOFF.write_text(text, encoding='utf-8')
    old_report = ROOT / 'docs/research/20261101_오후_독립연구_결과보고.md'
    report = old_report.read_text().replace(OLD_PROPOSAL, NEW_PROPOSAL)
    if '## 7. 사용자106 승인 이후의 상태' not in report:
        report += (chr(10) + '## 7. 사용자106 승인 이후의 상태' + chr(10)*2 +
                   '위 본문은 오후 연구 마감 당시의 기록이다. 이후 사용자106이 A 수정·CPU 검증·커밋·보고만 승인했고, '
                   '공유 collector와 자식 경계를 구현했다. 현재 상태와 실제 전후 비교는 [최종 보고](20261101_자율주도_연구_최종보고.md)를 따른다. '
                   '새 GPU·모델·전체 스모크는 수행하지 않았다.' + chr(10))
    old_report.write_text(report, encoding='utf-8')
    if sha(WIP) != wip_sha:
        raise ValueError('WIP changed during read-only synchronization')
    final = rows(HANDOFF.read_text())
    if len(final) != 106 or any(final[k][1] != board[k][1] for k in board):
        raise ValueError('all 106 original directives must match exactly')
    with receipt.open('x', encoding='utf-8') as stream:
        json.dump(dict(phase=phase, wip_read_only=True, wip_sha256=wip_sha,
                       original_directives=106, handoff_before=before,
                       handoff_after=sha(HANDOFF)), stream, indent=2)
    print('HANDOFF_SYNC', phase, 'directives=106 WIP unchanged')


if __name__ == '__main__':
    main()
