"""Keep guard5 disjoint save; index row shards locally without staging them."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
from selection_metadata_store_v1 import SelectionStore, bound_selection_loads

frozen5 = AUDIT/'prepare_versioned_checkpoint_v5.py'
raw5 = frozen5.read_bytes()
assert hashlib.sha256(raw5).hexdigest().upper() == '2F1EBFF5A1CF4953A4DA199ED40F3D944A4E7EA5793AE6C70EA2B762C4500603'
assert hashlib.sha256((AUDIT/'selection_metadata_store_v1.py').read_bytes()).hexdigest().upper() == 'A5DE169B5493EDB1AD4FF456145BA0BF729754670FF258BADD2AFC67CC89E461'
config_path = (ROOT/sys.argv[sys.argv.index('--config') + 1]).resolve()
assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
config = json.loads(config_path.read_bytes())
selection_path = AUDIT/config['selection']
selection = SelectionStore(AUDIT).read(selection_path, config['selection_sha256'])
prior = selection['prior_selection']
bindings = [(selection_path, config['selection_sha256']), (ROOT/prior['path'], prior['sha256'])]
with bound_selection_loads(bindings, directory=AUDIT):
    # Execute only frozen guard5 preflight, then frozen4's source transformer.
    text5 = raw5.decode('utf-8')
    last5 = "exec(compile(raw,str(frozen),'exec'),dict("
    assert text5.count(last5) == 1
    scope5 = dict(__name__='checkpoint6_guard5_preflight', __file__=str(Path(__file__)))
    exec(compile(text5.split(last5)[0], str(frozen5), 'exec'), scope5)
    raw4 = scope5['raw']
    assert hashlib.sha256(raw4).hexdigest().upper() == '1BF6B748A7FF61EC9D83ED6910B7D11167516BBF9B7B0839C04EAB7F2038B96A'
    text4 = raw4.decode('utf-8')
    last4 = "exec(compile(code, str(scope['frozen']), 'exec'),"
    assert text4.count(last4) == 1
    scope4 = dict(__name__='checkpoint6_existing_save_transform', __file__=str(Path(__file__)))
    exec(compile(text4.split(last4)[0], str(scope5['frozen']), 'exec'), scope4)
    code = scope4['code']
    owned_script_paths = (
        'scripts/p106b_hold_resolution_review_safeguards_v4.py',
        'scripts/p106b_hold_resolution_disambiguation_v1.py',
        'scripts/p106b_hold_resolution_policy_v27.py',
        'scripts/test_p106b_hold_resolution_policy_v27.py',
    )
    owned_anchor = "assert name == 'scripts/p106b_hold_resolution_review_safeguards_v4.py'"
    assert code.count(owned_anchor) == 1
    code = code.replace(owned_anchor, 'assert name in ' + repr(owned_script_paths))
    anchor = "inv.write_json(AUDIT/f'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V{version}.json',"
    assert code.count(anchor) == 1
    addition = """physical_selection_header=json.JSONDecoder().decode(selection_path.read_text(encoding='utf-8'))
if physical_selection_header.get('selection_storage_schema') == 'TINYLM_SELECTION_ROWS_V1':
    for shard_pin in physical_selection_header['row_shards']:
        shard_path=AUDIT/shard_pin['path']
        assert shard_path.resolve().is_relative_to(AUDIT/'selection_metadata_row_shards_v1')
        assert not shard_path.is_symlink() and inv.file_sha(shard_path)==shard_pin['sha256']
        assert shard_path.stat().st_size==shard_pin['bytes']<20_000_000
        metadata.append(dict(path=str(shard_path.relative_to(ROOT)),sha256=shard_pin['sha256'],bytes=shard_pin['bytes'],meaning='LOCAL_ONLY_SELECTION_ROW_METADATA_FRAGMENT_NOT_CORPUS_TXT'))
"""
    code = code.replace(anchor, addition + anchor)
    exec(compile(code, str(scope4['scope']['frozen']), 'exec'), dict(
        __name__='guard5_sharded_selection_owned_checkpoint', __file__=str(Path(__file__))))
    scope5['assert_no_protected_opens']()
