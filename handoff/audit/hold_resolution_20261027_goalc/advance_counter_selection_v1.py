"""Advance a pinned batch through the existing admission procedure."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
config=json.loads(config_path.read_bytes());number=config['next_selection'];prior_number=config['prior_selection']
assert isinstance(number,int) and number==prior_number+1 and 14<=number<=9999
assert re.fullmatch(r'v[1-9][0-9]*',config['snapshot_version'])
template=AUDIT/'prepare_root13_counter_batch002_selection_v1.py'
assert hashlib.sha256(template.read_bytes()).hexdigest().upper()=='37D9FE09D967AD6B7633459B08902000AA85D4B1F55C1022DD28B5F8804C2D2A'
source=template.read_text(encoding='utf-8')
last="exec(compile(code,str(frozen),'exec'),environment)"
assert source.count(last)==1
# Execute only the frozen source transformer, never its old admission run.
scope=dict(__name__='counter_selection_transform_only',__file__=str(Path(__file__)))
exec(compile(source.split(last)[0],str(template),'exec'),scope)
code=scope['code'];environment=scope['environment']


def once(before,after):
    global code
    assert code.count(before)==1,('frozen admission anchor changed',before)
    code=code.replace(before,after)


once("previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'",f"previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V{prior_number}.json'")
once("'C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'",repr(config['prior_selection_sha256']))
once("'v5/complete.json'",repr(config['snapshot_version']+'/complete.json'))
once("'29C96805441C5CC141EBA7032161790838F414894D63D98C09F94430C3D9FE30'",repr(config['snapshot_sha256']))
once("out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V13.json'",f"out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V{number}.json'")
for before,after in {
    'ROOT13_COUNTER_BATCH002_CLOSURE_V1':config['closure_stem'],
    'ROOT13_COUNTER_BATCH002_ADMISSION_SCOPE_V1':config['scope_stem'],
    'PRIOR_ROOT12_UNCHANGED_PLUS_EXACT_INDEPENDENT_COUNTER_BATCH002':f'PRIOR_ROOT{prior_number}_UNCHANGED_PLUS_PINNED_COUNTER_AND_CONTEXT_REPAIRS'}.items():
    assert before in code;code=code.replace(before,after)
extra_code="""extra_manifest_paths=[];extra_selected_count=0
if EXTRAS_PATH is not None:
    assert inv.file_sha(EXTRAS_PATH)==EXTRAS_SHA
    extras=inv.cache.read(EXTRAS_PATH)
    assert extras['independent_root_context_review_completed'] is True
    assert extras['additional_Luna_counter_review_claimed'] is False and extras['guard_waivers']==0
    for item in extras['records']:
        assert item['id'] not in guard['restricted_ids']
        assert all(pin['sha256'] not in guard['restricted_hashes'] for pin in [item['original'],item['body']])
        assert item['root_approved'] is True and all(item['guards'].values())
    for name,expected in extras['input_pins'].items():assert inv.file_sha(ROOT/name)==expected
    for item in extras['records']:
        key=item['id'];original=item['original'];body=item['body']
        assert key not in sources and key not in prior_ids
        assert original['sha256'] not in prior_hashes
        manifest_extra=inv.BASE/item['original_primary_cohort']/'manifest.json'
        extra_manifest_paths.append(manifest_extra)
        source_extra=next(r for r in inv.cache.read(manifest_extra)['rows'] if r['id']==key)
        assert source_extra['original']['sha256']==original['sha256']
        assert inv.file_sha(ROOT/body['path'])==body['sha256']
        evidence=dict(path=str(EXTRAS_PATH.relative_to(ROOT)),sha256=EXTRAS_SHA)
        choice=dict(cohort=item['original_primary_cohort'],decision='EDIT',body=body['path'],
            clean_text_sha256=body['sha256'],original=original,review=item['review'],
            reason=item['semantic_reason'],author_output=None,compare_source=None,root_approved=True,
            primary_review=item['review'],independent_root_context_evidence=evidence)
        selected.append(dict(id=key,original_text_sha256=original['sha256'],selected=choice,
            original_paths=[original],root_approved=True,cache_admitted=False,
            status='EXACT_AUTHOR_REPAIR_PLUS_INDEPENDENT_ROOT_CONTEXT_REVIEW',guard_closure_id=CLOSURE_STEM))
        checks.append(dict(id=key,original=original,body=body,primary_review=item['review'],
            counter_review=None,independent_root_context_evidence=evidence,guards=item['guards'],
            raw_guards=item['raw_guards'],individual_closure=item.get('individual_order_closure'),numeric_flags=item['numeric_flags']))
        positions+=source_extra['occurrences'];extra_selected_count+=1
all_rows=previous['rows']+selected"""
once("all_rows=previous['rows']+selected",extra_code)
once('input_paths=[manual_path,frozen_path,previous_path,snapshot_path,manifest_path,guard_path,Path(__file__),',
    'input_paths=[CONFIG_PATH,TEMPLATE_PATH]+extra_manifest_paths+([EXTRAS_PATH] if EXTRAS_PATH else [])+[manual_path,frozen_path,previous_path,snapshot_path,manifest_path,guard_path,Path(__file__),')
once('    full_source_context_review_by_distinct_Luna_roles=True,root_training_TXT_authored=0,',
    "    full_source_context_review_by_distinct_Luna_roles='COUNTER_SUBSET_ONLY',"+chr(10)+
    '    additional_root_independent_context_sources=extra_selected_count,additional_Luna_counter_review_claimed_for_extra=False,root_training_TXT_authored=0,')
once('inv.write_json(out,document)',
    "document['additional_root_independent_context_sources']=extra_selected_count"+chr(10)+
    "payload=(json.dumps(document,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')"+chr(10)+
    "if len(payload)>=20_000_000:payload=(json.dumps(document,ensure_ascii=False,separators=(',',':'))+chr(10)).encode('utf-8')"+chr(10)+
    "assert len(payload)<20_000_000,'selection needs a separately validated sharded schema before creation'"+chr(10)+
    "with out.open('xb') as stream:stream.write(payload)")
once("print('ROOT13',inv.file_sha(out))",f"print('ROOT{number}',inv.file_sha(out))")
extra_path=(ROOT/config['extra_context_proof']).resolve() if config.get('extra_context_proof') else None
assert extra_path is None or extra_path.is_relative_to(AUDIT)
environment.update(CONFIG_PATH=config_path,TEMPLATE_PATH=template,EXTRAS_PATH=extra_path,
    EXTRAS_SHA=config.get('extra_context_proof_sha256'),CLOSURE_STEM=config['closure_stem'])
exec(compile(code,str(template),'exec'),environment)
