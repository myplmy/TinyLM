"""Capture exact final document/ledger checks without broad repository scanning."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE=Path('handoff/audit/nov04_p107_cli')
WIP=Path('handoff/WIP_20261022_작업원장.md')
HANDOFF='handoff/202611042233_HANDOFF.md'
PREVIOUS='handoff/202611011123_HANDOFF.md'
OUTPUT=BASE/'FINAL_DOCUMENT_CHECKS_v3.json'
if OUTPUT.exists():raise FileExistsError(OUTPUT)
checks=[
    ('handoff',[sys.executable,'-I','-B','.agents/skills/session-handoff/scripts/check_handoff_codex.py',HANDOFF]),
    ('handoff_queue',[sys.executable,'-B','-X','utf8','scripts/handoff_queue.py','--audit',HANDOFF,'--previous',PREVIOUS]),
    ('handoff_time',[sys.executable,'-B','-X','utf8','scripts/handoff_time.py',HANDOFF]),
    ('result_conditions',[sys.executable,'-B','-X','utf8','scripts/check_result_conditions.py',
        'test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md',
        'test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md']),
    ('result_closure',[sys.executable,'-B','-X','utf8','scripts/check_result_closure.py','--manifest',str(BASE/'RESULT_CLOSURE_v1.json')]),
    ('wip_capsule',[sys.executable,'-B','-X','utf8','scripts/wip.py','--file',str(WIP),'--capsule-check']),
]
before=hashlib.sha256(WIP.read_bytes()).hexdigest().upper()
rows=[]
for name,argv in checks:
    result=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',check=False)
    rows.append(dict(name=name,argv=argv,actual_exit=result.returncode,stdout=result.stdout,stderr=result.stderr))
after=hashlib.sha256(WIP.read_bytes()).hexdigest().upper()
errors=[r['name'] for r in rows if r['actual_exit']!=0]
if before!=after:errors.append('wip_changed_during_readonly_validation')
value=dict(schema='P107_P108_FINAL_DOCUMENT_CHECKS_V1',actual_exit=0 if not errors else 1,
    wip=str(WIP),wip_sha256=before,wip_unchanged=before==after,
    handoff=HANDOFF,handoff_sha256=hashlib.sha256(Path(HANDOFF).read_bytes()).hexdigest().upper(),
    checks=rows,errors=errors,model_loads=0,cuda_calls=0,global_static_pass=False)
with OUTPUT.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps(dict(actual_exit=value['actual_exit'],checks=len(rows),errors=errors,wip_unchanged=before==after)))
raise SystemExit(value['actual_exit'])
