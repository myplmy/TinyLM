"""Verify the final UI-only revision and source-linked numeric preservation."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];A=Path(__file__).resolve().parent
B=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc';pins={}
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(A))
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_inventory as inv
from numeric_atom_integrity_v1 import numeric_atom_changes


def raw(path,expected):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    value=path.read_bytes();digest=hashlib.sha256(value).hexdigest().upper();assert digest==expected
    pins[str(path.relative_to(ROOT))]=digest;return value


guard=json.loads(raw(A/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json','7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'))
assert 'expanded_train:189258' not in guard['restricted_ids']
specs=[('original',B/'remaining_field_title_native_proofs_v1/pages/page_010/inputs/expanded_train_189258_original.txt','B7C5F06D0E413CF20C69F9B4EDE11B335C567340D7A7A189B1E3C67C38F6C5CD'),('v3',B/'exact_cohort_rendered_v1/BB/BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E.txt','BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E'),('v4',B/'exact_cohort_rendered_v1/F5/F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E.txt','F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E'),('v5',B/'exact_cohort_rendered_v1/10/10829E26FB74757CC37774B62F9CCB36A0D29422FEF0D806CF35EEE5CA9C4925.txt','10829E26FB74757CC37774B62F9CCB36A0D29422FEF0D806CF35EEE5CA9C4925')]
assert all(s not in guard['restricted_hashes'] for _,_,s in specs)
texts={name:raw(path,digest).decode('utf-8') for name,path,digest in specs}
before=texts['v4'];after=texts['v5'];ui='.PDF File (Adobe PDF File), 1187 KB'
assert before.count('Conflicts of Interest\n')==1 and before.count(ui)==1
expected=before.replace('Conflicts of Interest\n','',1).replace(ui,'',1)
tags=['[FREE Full text]','[CrossRef]','[Medline]'];removed={}
for tag in tags:
    removed[tag]=expected.count(' '+tag);expected=expected.replace(' '+tag,'')
assert expected.count('published 02.11.20Copyright')==1
expected=expected.replace('published 02.11.20Copyright','published 02.11.20\nCopyright',1)
assert expected==after,'v5 contains a change outside its approved UI and line-boundary edits'
pattern=r'[-+–−]?(?:\d+(?:\.\d*)?|\.\d+)'
numbers={key:re.findall(pattern,value) for key,value in texts.items()}
assert numbers['original']==numbers['v3']==numbers['v4']
assert texts['original'].count(ui)==1
assert re.findall(pattern,texts['original'].replace(ui,''))==numbers['v5']
assert len(numbers['original'])==624 and len(numbers['v5'])==623
assert texts['original'][texts['original'].index('©Mahboube'):].strip()==after[after.index('©Mahboube'):].strip()
assert after.endswith('\n')
for label in ['Physical function','Psychological function','Social function','Total']:
    assert '|'+label+'|\n|Before, mean (SD)|' in after
    assert '|'+label+' — Before|' in after and '|'+label+' — After|' in after
for label in ['Group variable','Income','Hospitalization']:
    assert '|Partial eta squared — '+label in after
assert '|Age (years)|\n|<40, n (%)||10 (18)||7 (13)|' in after
assert '|Education level|\n|Elementary to high school||46.20 (15.69)|' in after
assert '|Income adequacy|\n|Somewhat adequate||43.57 (14.72)|' in after
numeric=numeric_atom_changes(texts['original'],after);assert not numeric
guards=dict(numeric_atoms=True,code=policy.code_preserved(texts['original'],after),unicode=policy.unicode_examples_preserved(texts['original'],after),style=policy.semantic_style_preserved(texts['original'],after),ordered=policy.ordered_deletion(texts['original'],after),no_memo=not bool(inv.corpus.MEMOS.search(after)))
guide=A/'ROOT_PRIMARY_189258_TABLE_REPAIR_SCOPE_V1.md';raw(guide,'11AA3FCED8D3B8512E02D8169D7F348742A32ABCCE697EC4220DC10B46A1782E')
for name in ['read_primary_189258_v4_v1.py','read_primary_189258_v5_v1.py',Path(__file__).name]:
    p=A/name;pins[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest().upper()
result=dict(status='PRIMARY_189258_V5_FULL_BODY_UI_DELTA_AND_NUMERIC_PRESERVATION_VERIFIED_NOT_ADMITTED',id='expanded_train:189258',body_sha256=specs[-1][2],body_characters=len(after),root_v5_body_full_read=True,root_v4_to_v5_full_character_diff_read=True,v4_to_v5_only_approved_changes=True,original_v3_v4_signed_numeric_tokens=624,v5_signed_numeric_tokens=623,removed_numeric_UI_only='1187 KB attachment size',study_and_reference_numeric_sequence_unchanged=True,new_numeric_values=0,removed_reference_UI_counts=removed,all_copyright_and_license_text_preserved=True,primary_reference_url='https://nursing.jmir.org/2020/1/e20747/',primary_reference_scope='Recovered table labels only; no imported numeric rows or efficacy reanalysis.',raw_source_guards=guards,remaining_step='Close the exact primary-source table transformations and join the reviewed selection; ordered source guard is not waived.',root_or_cache_new_admissions=0,guard_waivers=0,whole_original_article_fact_pass=False,model_or_clinical_code_runs=0,input_pins=pins,goal_complete=False,training_authorized=False)
payload=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8');assert len(payload)<20000000
with (A/'PRIMARY_189258_V5_FORMAT_AND_NUMERIC_VERIFIED_V1.json').open('xb') as f:f.write(payload)
print(json.dumps({'status':result['status'],'raw_guards':guards,'sha256':hashlib.sha256(payload).hexdigest().upper()}))
