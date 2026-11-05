"""Exercise five fixed V4 wrappers using metadata and pre-payload rejections only."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
scope_path=AUDIT/'LOSSLESS_REVIEW_READER_SCOPE_V2.json'
assert hashlib.sha256(scope_path.read_bytes()).hexdigest().upper()=='316F2E46B2D84090FE03EAA2C2BD03774E690DA5CFEBD37D40E2AFBB795EAEB6'
scope=json.loads(scope_path.read_bytes())
guard=json.loads((ROOT/scope['contract']['path']).read_bytes())
specs=[('context_controls','c','root12_independent_admission_counter_v1','expanded_train:33141'),
       ('context_latin','l','root12_independent_admission_counter_v1','expanded_train:98341'),
       ('context_hangul','h','remaining_field_title_page_013_counter_v1',None),
       ('historical_review','j','remaining_field_title_page_012_counter_v1','expanded_train:257919'),
       ('legacy_review','g','remaining_field_title_page_012_counter_v1','expanded_train:241493')]
positives=[];negatives=[]
for role,short,cohort,ident in specs:
    pin=scope['roles'][role][cohort];path=ROOT/pin['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==pin['sha256']
    manifest=json.loads(path.read_bytes())
    if ident is None:ident=next(row['id'] for row in manifest['rows'] if row['role']==role)
    source=next(row for row in manifest['rows'] if row['id']==ident)
    assert source['role']==role and ident not in guard['restricted_ids']
    assert all(source[label]['sha256'] not in guard['restricted_hashes'] for label in ['original','candidate'])
    args=[ident,'pair','1']
    if short in {'h','j','g'}:args.insert(0,str(int(cohort.split('_page_')[1].split('_')[0])))
    command=['bash',str(ROOT/f'tmp/hold-{short}-lossless-v2'),*args,'--check-only']
    before=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True)
    assert result.returncode==0,result.stderr.decode('utf-8')
    value=json.loads(result.stdout)
    assert value['source_id']==ident and value['role']==role and value['payload_opens']==0
    positives.append(dict(role=role,short=short,cohort=cohort,id=ident,command=command,
        seconds=time.monotonic()-before,original=value['original'],candidate=value['candidate'],payload_opens=0))
for ident in guard['restricted_ids']:
    command=['bash',str(ROOT/'tmp/hold-c-lossless-v2'),ident,'pair','1']
    result=subprocess.run(command,cwd=ROOT,capture_output=True)
    assert result.returncode!=0 and b'restricted source ID; no payload read' in result.stderr
    negatives.append(dict(id=ident,observed_exit_code=result.returncode,restricted_ID_precedes_payload=True))
result=subprocess.run(['bash',str(ROOT/'tmp/hold-l-lossless-v2'),'expanded_train:33141','pair','1'],cwd=ROOT,capture_output=True)
assert result.returncode!=0 and b'source belongs to another assigned role' in result.stderr
value=dict(status='FIVE_V2_METADATA_PREFLIGHTS_AND_NINE_ACTUAL_PROTECTED_ID_DENIALS_PASS',
    positives=positives,restricted_ID_denials=negatives,wrong_role_denied_before_payload=True,
    original_or_candidate_payload_files_opened=0,actual_agent_trial_complete=False,
    training_TXT_writes=0,goal_complete=False,training_authorized=False)
out=AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPERS_RUNTIME_V2.json';assert not out.exists()
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(dict(status=value['status'],roles=len(positives),denials=len(negatives),
    payload_opens=0,sha256=hashlib.sha256(out.read_bytes()).hexdigest().upper())),flush=True)
