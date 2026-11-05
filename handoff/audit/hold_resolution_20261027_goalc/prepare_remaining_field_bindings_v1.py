"""Pin every remaining field assignment once, with seven fixed guard5 aliases."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(AUDIT));sys.path.insert(0,str(ROOT))
from active_guard_v5_preflight_v1 import checked_contract,CONTRACT,EXPECTED
from scripts import p106b_hold_resolution_inventory as inv
checked_contract()


def pin(path):
    assert not path.is_symlink()
    return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),bytes=path.stat().st_size)


def write(path,value):
    assert not path.exists()
    inv.write_json(path,value)
    assert path.stat().st_size<20_000_000
    return pin(path)


old_path=AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPER_MANIFEST_V5.json'
assert inv.file_sha(old_path)=='AF89B115F8C12E89BB7B363808D6821663D5AD44787884FDE520154F81517870'
old=inv.cache.read(old_path);old_scope_path=ROOT/old['scope']['path']
assert pin(old_scope_path)==old['scope'];scope=inv.cache.read(old_scope_path)
assert scope['contract']['sha256']==EXPECTED
index_path=inv.BASE/'remaining_field_title_readers_v1/complete.json'
assert inv.file_sha(index_path)=='DB50BC5AF86F57B0158E1D904D45EF1E6BC1653D6A0808F4E2B88FC90F8BBE57'
index=inv.cache.read(index_path);assert len(index['pages'])==36 and index['sources']==18237
roles={'c':'context_controls','l':'context_latin','h':'context_hangul','j':'historical_review','g':'legacy_review'}
current={'context_controls':None,'context_latin':None,'context_hangul':15,'historical_review':14,'legacy_review':13}
bindings=[];pinned_inputs={pin(p)['path']:pin(p)['sha256'] for p in [old_path,old_scope_path,index_path,CONTRACT,Path(__file__)]}
for page in index['pages']:
    if page['page']<12:continue
    path=ROOT/page['path'];assert inv.file_sha(path)==page['sha256']
    manifest=inv.cache.read(path);group=page['group']
    assert path==inv.BASE/group/'manifest.json'
    assert len(manifest['rows'])==page['sources']
    by_id={r['id']:r for r in manifest['rows']};assert len(by_id)==len(manifest['rows'])
    for short,role in roles.items():
        assignment=manifest['assignments'][role]
        ids=assignment['ids'] if isinstance(assignment,dict) else assignment
        assert len(ids)==len(set(ids)) and all(by_id[key]['role']==role for key in ids)
        scope['roles'][role][group]=pin(path)
        directory=inv.BASE/'agents'/role/group;tasks=[]
        for number in range(1,(len(ids)+4)//5+1):
            task=directory/f'TASK_{number:03d}.md'
            assert task.resolve().is_relative_to(inv.BASE/'agents'/role)
            tasks.append(pin(task))
        bindings.append(dict(role=role,agent='/root/hold_'+short+'_resume_v2',page=page['page'],
            cohort=group,manifest=pin(path),ids=ids,count=len(ids),task_count=len(tasks),
            tasks=tasks,first_id=ids[0],last_id=ids[-1],output_directory=str(directory.relative_to(ROOT)),
            initial_current_page=current[role],root12_must_finish_first=role in ['context_controls','context_latin']))
scope.update(authority='기존5역할의field12~36정확원문배정;현재커서계속/완료페이지재시작금지',
    previous_fixed_scope=old['scope'],same_entry_core_and_guard=True)
scope_pin=write(AUDIT/'LOSSLESS_REVIEW_READER_SCOPE_V6.json',scope)
entry=old['entry'];assert pin(ROOT/entry['path'])==entry
old_aliases={Path(r['path']).name:r for r in old['aliases']}
aliases=[]


def alias(template_path,target_name,role=None):
    p=ROOT/template_path;item=old_aliases[p.name];assert pin(p)==item
    code=p.read_text(encoding='utf-8')
    for before,after in [(old['scope']['path'],scope_pin['path']),
        (old['scope']['sha256'],scope_pin['sha256']),
        ('"bytes":'+str(old['scope']['bytes']),'"bytes":'+str(scope_pin['bytes']))]:
        assert code.count(before)==1;code=code.replace(before,after)
    if role is not None and role!='context_hangul':
        assert code.count('"context_hangul"')==1
        code=code.replace('"context_hangul"',json.dumps(role))
    target=ROOT/'tmp'/target_name;assert not target.exists()
    with target.open('x',encoding='utf-8') as stream:stream.write(code)
    aliases.append(pin(target))


for short in ['c','l']:
    alias('tmp/hold-'+short+'-lossless-v5','hold-'+short+'-lossless-v6')
for short,role in roles.items():
    alias('tmp/hold-h-lossless-v5','hold-'+short+'-field-lossless-v6',role)
binding=write(AUDIT/'RESUME_REMAINING_FIELD_ROLE_BINDINGS_V2.json',dict(
    status='ALL_FIELD12_TO36_EXACT_ROLE_ASSIGNMENTS_BOUND_WITH_CURRENT_CURSOR_PRESERVED',
    current_pages=current,root12_then_field12_roles=['context_controls','context_latin'],
    roles=bindings,scope=scope_pin,entry=entry,guard_sha256=EXPECTED,
    allowed_operations='지정 V6 별칭과 자기 새 TXT/MD 및 PROGRESS만',
    forbidden='코드·시험·GPU·모델·학습·Git·삭제·기존원형/후보/본문덮기·보호/타역할접근',
    input_pins=pinned_inputs,source_original_or_candidate_reads=0,goal_complete=False,training_authorized=False))
fixed=write(AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPER_MANIFEST_V6.json',dict(
    status='SEVEN_FIXED_GUARD5_ALIASES_WITH_FULL_REMAINING_FIELD_ASSIGNMENTS',
    scope=scope_pin,entry=entry,aliases=aliases,guard_contract_sha256=EXPECTED,binding=binding,
    corpus_TXT_writes=0,actual_agent_application=False,goal_complete=False,training_authorized=False))
print(json.dumps(dict(binding=binding,scope=scope_pin,manifest=fixed,aliases=len(aliases),
    assignments=len(bindings),source_role_pairs=sum(r['count'] for r in bindings),payload_reads=0)))
