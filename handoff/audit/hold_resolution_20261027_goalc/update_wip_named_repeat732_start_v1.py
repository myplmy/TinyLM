"""Record the entire new repeat strata, without promoting native proof to admission."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
artifact='data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_named_roles_counter_v2/manifest.json'
for field in ['작업 내용','산출물','이어받을 지점']:
    lines=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(lines)==1
    before=lines[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    if field=='작업 내용':
        after=before+' 후속반복21727고유를전량재계수해지정층732고유/1117위치를선정했다. native732전부원문/후보재생성일치이며다른검사통과370고유/534위치는진단일뿐채택이아니다. 다섯Luna에146/147/146/146/147개전량을30TASK씩배정해판독중이며원문동일과정제적합성을구분하고명확한UI·미상귀속을추가수정중이다. 현재생성중인v2캐시에이후속732를미리편입하지않는다.'
    elif field=='산출물':
        after=before+'; handoff/audit/hold_resolution_20261027_goalc/REPEAT_REMAINING_FULL_STRATA_SCOPE_V2.md; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_remaining_named_strata_v2/complete.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_remaining_native_proofs_v2/complete.json; '+artifact
    else:
        after='진행중cache_reviewed_partial_v2의실제종료코드/built를회수해독립소비자·보호11metadata검산과전량재계측을수행한다. 별도로반복지정층732고유/1117위치의30TASK씩전체판독을회수하고UI/빈표/저자귀속중재·정확출력결합·본문가드·코드/Unicode/의미손실검토후새ROOT11로연결한다. 94e59e8d는676경로중간저장이고현재WIP·후속영수증/새코드는다음한국어커밋으로보존한다. 미결73668고유/115526위치는아직UNRESOLVED_NOT_ADMITTED이며다른큰유형복구도계속한다. 부분캐시나판독묶음종료를전체goal완료/일시중지로바꾸지않는다.'
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','전체반복층재계수·732native일치·다섯역할전량판독착수및캐시분리기록',
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU분석/관련새파생자료허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
