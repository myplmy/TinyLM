"""Reuse v2 with active guard4 and the exact previously adjudicated ID74 pair."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
from exact_counter74_numeric_context_v1 import verify_exact_context

activate()
frozen = AUDIT/'advance_counter_selection_v2.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'E7E36447766CB91028F6B6C253783B9BEC1EB08244BA264DF938F358864A3713'
text = raw.decode('utf-8')
last = "exec(compile(code,str(adapter),'exec'),environment)"
assert text.count(last) == 1
scope = dict(__name__='guard4_counter_selection_transform', __file__=str(Path(__file__)))
exec(compile(text.split(last)[0], str(frozen), 'exec'), scope)
code, environment = scope['code'], scope['environment']
config, ROOT = scope['config'], scope['ROOT']
proof_path = (ROOT/config['exact_numeric_context_proof']).resolve()
assert proof_path.is_relative_to(AUDIT) and not proof_path.is_symlink()
raw = proof_path.read_bytes()
digest = hashlib.sha256(raw).hexdigest().upper()
assert digest == config['exact_numeric_context_proof_sha256']
proof = json.loads(raw)
assert proof['guard_waivers'] == proof['root_training_TXT_authored'] == 0
assert proof['generic_numeric_guard_changed'] is False
assert len(proof['records']) == 1
numeric = proof['records'][0]
for name, expected in proof['input_pins'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper() == expected, name


def once(before, after):
    global code
    assert code.count(before) == 1, ('frozen admission anchor changed', before)
    code = code.replace(before, after)


once("guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'",
     "guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'")
once('7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306',
     '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D')
once('    raw_guards=dict(guards);individual_closure=None',
     '    raw_guards=dict(guards);individual_closure=None;numeric_context_closure=None')
anchor = "    checks.append(dict(id=key,original=source['original'],body=dict(path=row['body'],sha256=row['clean_text_sha256']),"
addition = """    if key == EXACT_NUMERIC['id']:
        assert guards['numeric_atoms'] is False
        verify_exact_context(EXACT_NUMERIC,key,source['original'],
            dict(path=row['body'],sha256=row['clean_text_sha256']),row['review'],original,body,numeric)
        guards['numeric_atoms']=True
        numeric_context_closure=dict(path=str(EXACT_NUMERIC_PATH.relative_to(ROOT)),sha256=EXACT_NUMERIC_SHA)
"""
once(anchor, addition + anchor)
once('individual_closure=individual_closure,numeric_flags=numeric))',
     'individual_closure=individual_closure,numeric_flags=numeric,numeric_context_closure=numeric_context_closure))')
once('input_paths=[EXACT_ORDER_PATH,ADAPTER_V1_PATH,CONFIG_PATH,TEMPLATE_PATH]',
     'input_paths=[EXACT_NUMERIC_PATH,NUMERIC_HELPER_PATH,ADAPTER_V2_PATH,ACTIVE_GUARD_PATH,EXACT_ORDER_PATH,ADAPTER_V1_PATH,CONFIG_PATH,TEMPLATE_PATH]')
once('closure=dict(status=', 'assert_no_protected_opens()' + chr(10) + 'closure=dict(status=')
once('    guard_failures_waived=0,checks=checks,input_pins=pins,',
     "    guard_failures_waived=0,active_guard_sha256='59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D'," + chr(10) +
     '    protected_payload_open_attempts=0,checks=checks,input_pins=pins,')
environment.update(EXACT_NUMERIC=numeric, EXACT_NUMERIC_PATH=proof_path, EXACT_NUMERIC_SHA=digest,
    verify_exact_context=verify_exact_context, assert_no_protected_opens=assert_no_protected_opens,
    NUMERIC_HELPER_PATH=AUDIT/'exact_counter74_numeric_context_v1.py', ADAPTER_V2_PATH=frozen,
    ACTIVE_GUARD_PATH=AUDIT/'active_guard_v4_preflight_v1.py')
exec(compile(code, str(frozen), 'exec'), environment)
assert_no_protected_opens()
