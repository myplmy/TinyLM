"""Record actual complete review coverage; keep the full goal running."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
ledger = ROOT / 'handoff/WIP_20261027_작업원장.md'
assert '01a17740-f435-7243-874c-2b5d58181c4c' in ledger.read_text(encoding='utf-8')
updates = [
    ('작업 내용', '전체goal active·1번진행을유지한다. 교차215·반복40·빈별칭223 전량478개검토행을수집55로회수해미저장0·새기계반려0을확인했다. 과거오류26건은보존했다. 계획32·preview3은4381개원문선택이나rootguard·cache는미완이다. 전문본문검산478은code0/Unicode0/style0/memo0위반이며숫자4·후속변형11·희귀빈필드를별도재판독했다. 추가14+12개검토행도전량수집56·계획33·본문검산26으로회수해새경로오류0·code0/Unicode0/style0/memo0위반을확인했다. 이26개는다른역할의독립전문판독도진행중이다. 보호7원문을디코딩하지않는metadatahelper의반례14시험과WIP31·capsule·경로8·TASK17·별칭V2 8시험은실제통과했다. 공식부분캐시H160219·draft26 P77639고유/122534위치·추가300M금지를유지하며새캐시검증전수치를승격하지않는다.'),
    ('산출물', 'handoff/audit/hold_resolution_20261027_goalc/supplemental_candidates_snapshot_v56.json; handoff/audit/hold_resolution_20261027_goalc/reviewed_selection_plan_v33.json; handoff/audit/hold_resolution_20261027_goalc/ROOT_AUTHORED_SELECTIONS_V10_PREVIEW3.json; handoff/audit/hold_resolution_20261027_goalc/JOIN_REPEAT_NOMINAL_BODY_AUDIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/POST_SEMANTIC_BODY_AUDIT_V1.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/post_semantic_independent_v1/manifest.json; handoff/audit/hold_resolution_20261027_goalc/GUARDED_CACHE_REBUILD_SCOPE_V1.md; handoff/audit/hold_resolution_20261027_goalc/guarded_scan_metadata_v1.py; handoff/audit/hold_resolution_20261027_goalc/RESUME_JOIN_CPU_CHECKS_V1.json'),
    ('이어받을 지점', '추가26개독립판독회수와source/body/review핀·실제diff를닫고4381개ROOT10을정확목적우선으로확정한다. 반복·부록·인용·API·줄바꿈의정당한검사예외는원문별근거를남긴다. 보호7과같은SHA다른위치도본문디코딩없이동결metadata로투영하는새cacheadapter를반례시험후연결한다. 전량v26·개별선택을전체297539고유/460695위치roster에적용해실제새별도캐시·독립소비자·전량재계측을수행하고잔여미처리복구를계속한다. 정본연쇄·한국어로컬커밋을실제근거로갱신한다. 미결을HOLD로개명해완료하거나부분묶음종료를전체일시중지로바꾸지않는다.'),
]
for field, after in updates[2:]:
    rows = [line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows) == 1
    before = rows[0].split('|')[{'작업 내용':4, '산출물':5, '이어받을 지점':6}[field]].strip()
    result = subprocess.run([sys.executable, '-I', '-B', str(ROOT/'scripts/wip.py'), '--override',
        '--file', str(ledger), '--item', '1', '--field', field, '--expect-before', before, '--set-after', after,
        '--reason', '전체478및후속26저장물검산과진행중인독립판독·보호metadata시험실적갱신',
        '--approval-ref', '사용자전체정제잔여HOLD완료까지재개지시와첨부목표CPU코드시험문서허가'],
        cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(result.returncode)
    print(field, 'CAS 완료')
