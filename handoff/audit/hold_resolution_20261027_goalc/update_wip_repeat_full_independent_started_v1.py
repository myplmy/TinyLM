"""Record actual complete binding and new independent reading, keeping goal RUN."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
ledger=ROOT/'handoff/WIP_20261027_작업원장.md'
exits=inv.cache.read(AUDIT/'EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V4.json')
assert len(exits['rows'])==3 and all(r['process_exit_code']==0 for r in exits['rows'])
for row in exits['rows']:assert inv.file_sha(ROOT/row['snapshot']['path'])==row['snapshot']['sha256']
export=inv.cache.read(AUDIT/'REPEAT_FULL_INDEPENDENT_READERS_EXIT_V1.json')
assert export['process_exit_code']==0 and export['sources']==732 and export['same_editor_reviewer']==0
terminal=inv.cache.read(AUDIT/'ROOT_REVIEWED_TERMINAL_HOLD15_V1.json')
assert terminal['unique_sources']==15 and terminal['source_positions']==15 and not terminal['new_roster_joined']
updates={
 '작업 내용':'전체goal active·1번진행이다. 공식새부분캐시v2는실생성0·독립소비자0이며원래H460695중K31985/E191835/X121349/H115526위치·잔여73668고유다. 채택1369110문서전량재생성·정확중복0·trainval본문교집합0·기준1145290본문보존·보호7/동일SHA11metadata전용검산을마쳤다. 후속반복732/1117위치의수집4는全732본문결합·미저장/미결/현재본문반려0이고과거오접두행4는보존했다. 실제본문검사732의code/Unicode/style/no_memo통과·미상주체/범위literal표시0이나순서삭제74표시는의미승인전이다. 출생2743/4273위치는수집4기준810저장/1933미저장·본문789/미결21이다. 무명15건은Luna1차와총괄원문전문2차판독으로개별검토완료HOLD15위치/1671rawID를기록했으나공식roster미연결이라115526는그대로다. 다른무명4건과달력2건은미결이다. 반복전량732를편집자와다른역할에재배정해독립검토2020패킷·다섯30TASK를실제생성0/자기검토0으로착수했고수집4기준40저장/692대기·현재반려0이다. 다섯역할은birth현재TASK마감뒤교차검토를우선하고완료후원래미결TASK로돌아간다. 1570명시경로8675450바이트를bbf07a3864a99bf31b8f24d58d359dcb7fb4ba6b로한국어로컬저장·전체변경집합/부모/바이트일치·index0검산후Git창을닫았다. 일부잘못된경로내용반환자기보고는독립미확인으로격리하고정확뷰/고정cat명령으로재판독했다. review023_v2덮기로빠진1265328행은이미커밋한원형archive에서새v3로복구·보조설명별도등록했다. 후속판독은ROOT11/새캐시미편입이며전체완료/일시중지/학습재개가아니다.',
 '산출물':'; handoff/audit/hold_resolution_20261027_goalc/VERIFIED_CACHE_FOLLOWUP_LOCAL_COMMIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_SNAPSHOTS_PROCESS_EXIT_V4.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_BODY_DIAGNOSTICS_V2.json; handoff/audit/hold_resolution_20261027_goalc/ROOT_REVIEWED_TERMINAL_HOLD15_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_REVIEW_MUTATIONS_V1.json; handoff/audit/hold_resolution_20261027_goalc/EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V1.json; handoff/audit/hold_resolution_20261027_goalc/REPEAT732_FULL_INDEPENDENT_SCOPE_V1.md; handoff/audit/hold_resolution_20261027_goalc/REPEAT_FULL_INDEPENDENT_READERS_EXIT_V1.json; handoff/audit/hold_resolution_20261027_goalc/INDEPENDENT_EXACT_CAT_COMMANDS_V1.json; handoff/audit/hold_resolution_20261027_goalc/FIXED_READER_1008072_SCOPE_RECEIPT_V1.json; data_cache/p106b_hold_resolution_v1_20261027_goalc/repeat_named_full_independent_v1/manifest.json',
 '이어받을 지점':'732全件の異なる役割による独立意味判読を回収し、現在中裁待ちのCalc/小惑星U/風力表/欠損発音記号等を原文で判断、実際本文と正確ガードを再確認してROOT11へ結合する。birthはcontrols22/hangul54/latin19/historical28/legacy44から再開し、1933未保存と既知無名4/暦2も完了させる。残り115526位置の他類型も継続する。'.replace('732全件の異なる役割による独立意味判読を回収し、現在中裁待ちのCalc/小惑星U/風力表/欠損発音記号等を原文で判断、実際本文と正確ガードを再確認してROOT11へ結合する。birthはcontrols22/hangul54/latin19/historical28/legacy44から再開し、1933未保存と既知無名4/暦2も完了させる。残り115526位置の他類型も継続する。','반복732전량의다른역할독립의미판독을회수하고중재대기Calc/소행성U/풍력표/소실발음기호등을원문으로판단,실제본문과정확가드를재확인해ROOT11로연결한다. birth는controls22/hangul54/latin19/historical28/legacy44부터재개하고1933미저장과기지무명4/달력2도끝낸다. 남은115526위치의다른유형도계속한다.')+' 원형HOLD와미판독을구분하고검증캐시/실패/복구/WIP를명시한국어로컬커밋으로이어저장한다. 일부노트의과거바이트보존미확인및잘못된경로반환자기보고의독립미확인을숨기지않는다. 현재컴팩트/부분캐시/중간저장을목표완료·일시중지로바꾸지않고추가300M·모델/GPU·보호TinyDataset·타세션전용자료·push/PR금지를유지한다.'}
for field,value in updates.items():
    rows=[line for line in ledger.read_text(encoding='utf-8').splitlines() if line.startswith('| **1** |')]
    assert len(rows)==1
    before=rows[0].split('|')[{'작업 내용':4,'산출물':5,'이어받을 지점':6}[field]].strip()
    after=before+value if field=='산출물' else value
    result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/wip.py'),'--override','--file',str(ledger),
        '--item','1','--field',field,'--expect-before',before,'--set-after',after,
        '--reason','실제732본문결합/810출생판독/732全量交差検討開始/韓国語commit検算と失敗復旧を接続'.replace('732全量交差検討開始/韓国語commit検算と失敗復旧を接続','732전량교차검토착수/한국어커밋검산과실패복구연결'),
        '--approval-ref','사용자전체정제잔여HOLD완료까지지시와첨부goal의CPU/관련문서허가'],
        cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        print(result.stdout,result.stderr)
        raise SystemExit(result.returncode)
    print(field,'CAS 완료')
