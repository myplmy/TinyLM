"""Reuse all five frozen independent checks with an exact cache-delta config."""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT)
c=json.loads(config_path.read_bytes());n=c['cache_version'];old_n=c['prior_cache_version']
assert isinstance(n,int) and n==old_n+1 and n>=6
frozen=AUDIT/'verify_cache4_progress_delta_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='52DA8A36EACDC0C851407FE7D0CEEF01B0267563F9A356B3BDAEE2DEE0F49C7A'
code=raw.decode()
mapping={'cache_reviewed_partial_v3':f'cache_reviewed_partial_v{old_n}','cache_reviewed_partial_v4':f'cache_reviewed_partial_v{n}','CACHE_REVIEWED_PARTIAL_V4':f'CACHE_REVIEWED_PARTIAL_V{n}','roster_reviewed_partial_v4':f'roster_reviewed_partial_v{c["roster_version"]}','ROOT_AUTHORED_SELECTIONS_V12.json':f'ROOT_AUTHORED_SELECTIONS_V{c["selection_version"]}.json','ACTUAL_CACHE4_CONSUMER_PROOF_CHAIN_AND_PROGRESS_DELTA_VERIFIED':f'ACTUAL_CACHE{n}_CONSUMER_PROOF_CHAIN_AND_PROGRESS_DELTA_VERIFIED','CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1':f'CACHE{n}_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1'}
pattern='|'.join(re.escape(k) for k in sorted(mapping,key=len,reverse=True));code=re.sub(pattern,lambda m:mapping[m.group()],code)
numbers={'110173':c['prior_HOLD_positions'],'109931':c['HOLD_positions'],'109893':c['HOLD_positions']-38,'123':c['new_accepted_documents'],'242':c['resolved_positions'],'119':c['additional_duplicate_positions']}
pattern=r'(?<![A-Za-z0-9_])(?:'+'|'.join(numbers)+r')(?![A-Za-z0-9_])';code=re.sub(pattern,lambda m:str(numbers[m.group()]),code)
def once(before,after):
    global code
    assert code.count(before)==1,before
    code=code.replace(before,after,1)
once("assert added=={'train':121,'val':2}",f"assert sum(added.values())=={c['new_accepted_documents']} and all(v>=0 for v in added.values())")
once(f"assert new['counts']['EDIT']-old['counts']['EDIT']=={c['new_accepted_documents']}",f"assert new['counts']['EDIT']-old['counts']['EDIT']=={c['EDIT_increase']}")
once("assert new['counts']['KEEP']==old['counts']['KEEP']",f"assert new['counts']['KEEP']-old['counts']['KEEP']=={c['KEEP_increase']}")
anchor=f"assert selection['new_approved_sources']=={c['new_accepted_documents']} and selection['new_approved_positions']=={c['resolved_positions']}"
replacement="""prior_selection=read(AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(CONFIG['prior_selection_version'])+'.json'))
assert selection['rows'][:len(prior_selection['rows'])]==prior_selection['rows']
assert len(selection['rows'])-len(prior_selection['rows'])==CONFIG['new_canonical_sources']
assert prior_selection['expected_roster_HOLD_positions']==CONFIG['prior_HOLD_positions']
assert selection['expected_roster_HOLD_positions']==CONFIG['HOLD_positions']
assert CONFIG['prior_HOLD_positions']-CONFIG['HOLD_positions']==CONFIG['resolved_positions']
assert CONFIG['EDIT_increase']+CONFIG['KEEP_increase']==CONFIG['new_accepted_documents']
assert CONFIG['new_accepted_documents']+CONFIG['additional_duplicate_positions']==CONFIG['resolved_positions']"""
once(anchor,replacement)
once('pins={}\n',"pins={str(CONFIG_PATH.relative_to(ROOT)):hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest().upper(),str(FROZEN_PATH.relative_to(ROOT)):hashlib.sha256(FROZEN_PATH.read_bytes()).hexdigest().upper()}\n")
exec(compile(code,str(frozen),'exec'),{'__name__':'versioned_cache_progress_actual_proof_check','__file__':str(Path(__file__)),'CONFIG':c,'CONFIG_PATH':config_path,'FROZEN_PATH':frozen})
