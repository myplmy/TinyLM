"""Keep role assignments/core3 exact; publish guard5 and five new fixed aliases."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent; ROOT = AUDIT.parents[2]
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import checked_contract,CONTRACT,EXPECTED
checked_contract()


def pin(path):
    raw=path.read_bytes();return dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(raw).hexdigest().upper(),bytes=len(raw))


def write(path,value):
    raw=(json.dumps(value,ensure_ascii=False,indent=2)+chr(10)).encode()
    assert len(raw)<20_000_000 and not path.exists()
    with path.open('xb') as stream:stream.write(raw)
    return pin(path)


old_manifest=AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPER_MANIFEST_V4.json'
assert pin(old_manifest)['sha256']=='3DC4DB6F15CDB071601655FF3AD43FDDABB86237E75B07EA9088CF6E7F68D25B'
old=json.loads(old_manifest.read_bytes())
scope_path=ROOT/old['scope']['path'];assert pin(scope_path)==old['scope']
scope=json.loads(scope_path.read_bytes());before_roles=scope['roles']
scope=dict(scope,contract=pin(CONTRACT),authority='기존5역할/core3 그대로, guard5의새2행과모든SHA/alias 차단',
    previous_fixed_scope=old['scope'],all_current_role_assignments_preserved=True)
scope_pin=write(AUDIT/'LOSSLESS_REVIEW_READER_SCOPE_V5.json',scope)
entry=pin(AUDIT/'scoped_lossless_review_entry_v4.py')
assert entry['sha256']=='1E4CA19CF2220910203F977B57315A1AACE072F073997C6B5BE215B60B1DEECB'
aliases=[]
for item in old['aliases']:
    path=ROOT/item['path'];assert pin(path)==item
    code=path.read_text(encoding='utf-8')
    for before,after in [(old['entry']['path'],entry['path']),
        (old['entry']['sha256'],entry['sha256']),(old['scope']['path'],scope_pin['path']),
        (old['scope']['sha256'],scope_pin['sha256']),
        ('"bytes":4886','"bytes":'+str(scope_pin['bytes']))]:
        assert code.count(before)==1,before
        code=code.replace(before,after)
    target=ROOT/item['path'].replace('-v4','-v5');assert not target.exists()
    with target.open('x',encoding='utf-8') as stream:stream.write(code)
    aliases.append(pin(target))
assert scope['roles']==before_roles
output=dict(status='FIXED_GUARD5_READER_SAME_CORE3_AND_EXACT_ROLE_ASSIGNMENTS',scope=scope_pin,
    entry=entry,aliases=aliases,guard_contract_sha256=EXPECTED,corpus_TXT_writes=0,
    actual_agent_application=False,input_pins={pin(p)['path']:pin(p)['sha256']
        for p in [Path(__file__),old_manifest,AUDIT/'active_guard_v5_preflight_v1.py']},
    goal_complete=False,training_authorized=False)
result=write(AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPER_MANIFEST_V5.json',output)
print(json.dumps(dict(scope=scope_pin,manifest=result,aliases=5,payload_reads=0)))
