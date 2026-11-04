"""Reuse v1 admission with pinned, individually verified grammar closures."""
from pathlib import Path
import hashlib, json
AUDIT=Path(__file__).resolve().parent
adapter=AUDIT/'advance_counter_selection_v1.py'
raw=adapter.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='A683C1BF524817A61E9BF520FA681D18680091DED9BFC3341B7FF1533ED0DD0B'
source=raw.decode();last="exec(compile(code,str(template),'exec'),environment)"
assert source.count(last)==1
scope={'__name__':'counter_v2_source_transform','__file__':str(Path(__file__))}
exec(compile(source.split(last)[0],str(adapter),'exec'),scope)
code=scope['code'];environment=scope['environment'];config=scope['config'];ROOT=scope['ROOT']
path=(ROOT/config['exact_order_context_proof']).resolve()
assert path.is_relative_to(AUDIT) and not path.is_symlink()
raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
assert digest==config['exact_order_context_proof_sha256']
proof=json.loads(raw);assert proof['guard_waivers']==0 and proof['training_TXT_authored_by_root']==0
closures={r['id']:r for r in proof['records']};assert len(closures)==len(proof['records'])
for name,expected in proof['input_pins'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper()==expected,name
anchor="    checks.append(dict(id=key,original=source['original'],body=dict(path=row['body'],sha256=row['clean_text_sha256']),"
assert code.count(anchor)==1
extra="""    if key in EXACT_CLOSURES:
        item=EXACT_CLOSURES[key]
        assert source['original']==item['original']
        assert row['body']==item['body']['path'] and row['clean_text_sha256']==item['body']['sha256']
        assert row['review']==item['review']
        assert guards==item['raw_guards'] and [name for name,value in guards.items() if not value]==['ordered']
        assert item['root_approved'] is True and item['guard_waiver'] is False
        assert item['root_source_and_new_body_and_full_diff_read'] is True and all(item['guards'].values())
        normalized=original
        for before,after in item['exact_substitutions']:
            assert normalized.count(before)==1
            normalized=normalized.replace(before,after,1)
        assert policy.ordered_deletion(normalized,body)
        guards['ordered']=True
        individual_closure=dict(path=str(EXACT_ORDER_PATH.relative_to(ROOT)),sha256=EXACT_ORDER_SHA)
"""
code=code.replace(anchor,extra+anchor)
anchor='input_paths=[CONFIG_PATH,TEMPLATE_PATH]';assert code.count(anchor)==1
code=code.replace(anchor,'input_paths=[EXACT_ORDER_PATH,ADAPTER_V1_PATH,CONFIG_PATH,TEMPLATE_PATH]')
environment.update(EXACT_CLOSURES=closures,EXACT_ORDER_PATH=path,EXACT_ORDER_SHA=digest,ADAPTER_V1_PATH=adapter)
exec(compile(code,str(adapter),'exec'),environment)
