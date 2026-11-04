"""Reuse the frozen first-batch closer, preserving every prior selection."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'prepare_root12_counter_batch001_selection_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='248EFC62D9478BC3F3BB418FABD35359BD55B826F4D4639AC87C028B1A70C716'
code=frozen.read_text(encoding='utf-8')


def once(before,after):
    global code
    assert code.count(before)==1,('frozen admission anchor changed',before)
    code=code.replace(before,after)


once("previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'","previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'")
once("'E07FF5FEB014BC81CC014D66B3DD547A07A57651BCF4745F3729E5EDEBB949DA'","'C93C6A8B29D5FB3EF9769346C1B37383FEE8F45557139324757793F42DD0759A'")
once("'v3/complete.json'","'v5/complete.json'")
once('snapshot=inv.cache.read(snapshot_path)',
    "assert inv.file_sha(snapshot_path)=='29C96805441C5CC141EBA7032161790838F414894D63D98C09F94430C3D9FE30'"+chr(10)+
    'snapshot=inv.cache.read(snapshot_path)')
once("manifest=inv.cache.read(manifest_path);sources={row['id']:row for row in manifest['rows']}",
    "assert inv.file_sha(manifest_path)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'"+chr(10)+
    "manifest=inv.cache.read(manifest_path);sources={row['id']:row for row in manifest['rows']}")
once('selected=[];checks=[];deferred=[];positions=0',
    "selected=[];checks=[];deferred=[];positions=0;preserved_ids=[]"+chr(10)+
    "prior_rows={row['id']:row for row in previous['rows']}"+chr(10)+
    "manual_path=AUDIT/'ROOT_1060968_EXACT_ORDER_CLOSURE_V1.json'"+chr(10)+
    "manual=inv.cache.read(manual_path)"+chr(10)+
    "assert manual['root_approved'] and not manual['guard_waiver']")
once("    assert key not in prior_ids and source['original_text_sha256'] not in prior_hashes",
    "    if key in prior_ids:"+chr(10)+
    "        assert row.get('clean_text_sha256')==prior_rows[key]['selected']['clean_text_sha256']"+chr(10)+
    "        preserved_ids.append(key);continue"+chr(10)+
    "    assert source['original_text_sha256'] not in prior_hashes")
anchor="    checks.append(dict(id=key,original=source['original'],body=dict(path=row['body'],sha256=row['clean_text_sha256']),"
replacement="""    raw_guards=dict(guards);individual_closure=None
    if key==manual['id']:
        assert source['original']['sha256']==manual['original']['sha256']
        assert row['clean_text_sha256']==manual['body']['sha256']
        assert [name for name,value in guards.items() if not value]==['ordered']
        assert manual['ordered_after_single_exact_punctuation_normalization'] is True
        guards['ordered']=True
        individual_closure=dict(path=str(manual_path.relative_to(ROOT)),sha256=inv.file_sha(manual_path))
    checks.append(dict(id=key,original=source['original'],body=dict(path=row['body'],sha256=row['clean_text_sha256']),"""
once(anchor,replacement)
once('counter_review=row[\'review\'],guards=guards,numeric_flags=numeric))',
    "counter_review=row['review'],guards=guards,raw_guards=raw_guards,individual_closure=individual_closure,numeric_flags=numeric))")
once('assert selected and len(selected)+len(deferred)==len(records)',
    'assert selected and len(selected)+len(deferred)+len(preserved_ids)==len(records)')
for before,after in [
 ('ROOT12_COUNTER_BATCH001_CLOSURE_V1','ROOT13_COUNTER_BATCH002_CLOSURE_V1'),
 ('ROOT_AUTHORED_SELECTIONS_V12.json\'\nassert not closure_path','ROOT_AUTHORED_SELECTIONS_V13.json\'\nassert not closure_path'),
 ('ROOT12_COUNTER_BATCH001_ADMISSION_SCOPE_V1','ROOT13_COUNTER_BATCH002_ADMISSION_SCOPE_V1'),
 ('PRIOR_ROOT11_UNCHANGED_PLUS_EXACT_INDEPENDENT_COUNTER_BATCH001','PRIOR_ROOT12_UNCHANGED_PLUS_EXACT_INDEPENDENT_COUNTER_BATCH002')]:
    code=code.replace(before,after)
once("input_paths=[previous_path,snapshot_path,manifest_path,guard_path,Path(__file__),",
    "input_paths=[manual_path,frozen_path,previous_path,snapshot_path,manifest_path,guard_path,Path(__file__),")
once("    snapshot_review_rows=len(records),root_approved_new_sources=len(selected),root_approved_new_positions=positions,",
    "    snapshot_review_rows=len(records),previously_approved_rows_preserved=len(preserved_ids),"+chr(10)+
    "    individual_exact_order_closures=sum(row['individual_closure'] is not None for row in checks),"+chr(10)+
    "    root_approved_new_sources=len(selected),root_approved_new_positions=positions,")
once('expected_roster_HOLD_unique=70230-len(selected),expected_roster_HOLD_positions=110173-positions,',
    "expected_roster_HOLD_unique=previous['expected_roster_HOLD_unique']-len(selected),"+
    "expected_roster_HOLD_positions=previous['expected_roster_HOLD_positions']-positions,")
once("print('ROOT12',inv.file_sha(out))","print('ROOT13',inv.file_sha(out))")
environment=dict(__name__='root13_counter_batch002_actual_run',__file__=str(Path(__file__)),frozen_path=frozen)
exec(compile(code,str(frozen),'exec'),environment)
