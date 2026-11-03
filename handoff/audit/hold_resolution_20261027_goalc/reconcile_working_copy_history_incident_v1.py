"""Preserve observed derived poststates and state missing prior-byte evidence."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
manifest_path=inv.BASE/'remaining_literal_full_counter_v1/manifest.json'
sources={row['id']:row for row in inv.cache.read(manifest_path)['rows']}
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
snapshot_path=inv.BASE/'remaining_literal_full_counter_v1_snapshots/v10/complete.json'
latest={}
for shard in inv.cache.read(snapshot_path)['shards']:
    path=ROOT/shard['path'];assert inv.file_sha(path)==shard['sha256']
    latest.update({row['id']:row for row in inv.cache.read(path)})
selected={row['id'] for row in inv.cache.read(AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')['records']}
directory=inv.BASE/'agents/context_controls/remaining_literal_full_counter_v1'
archive=inv.BASE/'working_copy_incident_poststate_v1';archive.mkdir(exist_ok=False)
rows=[]
for ident in ('expanded_train:1316467','expanded_train:1319447'):
    source=sources[ident]
    assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
    for kind in ('original','candidate'):
        assert inv.file_sha(ROOT/source[kind]['path'])==source[kind]['sha256']
    prefix=ident.replace(':','_')+'_literal_working_'
    v2=directory/(prefix+'v2.txt');v3=directory/(prefix+'v3.txt')
    assert v2.is_file() and v3.is_file()
    data=v2.read_bytes();assert 0<len(data)<20_000_000
    target=archive/v2.name
    with target.open('xb') as stream:stream.write(data)
    assert inv.file_sha(target)==inv.file_sha(v2)
    assert inv.file_sha(v3)==latest[ident]['clean_text_sha256']
    assert inv.file_sha(ROOT/latest[ident]['body'])==latest[ident]['clean_text_sha256']
    assert ident not in selected
    rows.append({'id':ident,'author_reported_prior_working_v2_mutation':True,
        'former_working_v2_sha256':None,'former_working_v2_exact_bytes_recovered':False,
        'limitation':'snapshot1–9에는이두ID의선택body/SHA가없었다. 이전v2의파일명보존을이전바이트보존으로주장하지않는다.',
        'observed_poststate':{'path':str(v2.relative_to(ROOT)),'sha256':inv.file_sha(v2)},
        'preserved_poststate_copy':{'path':str(target.relative_to(ROOT)),'sha256':inv.file_sha(target)},
        'current_v3':{'path':str(v3.relative_to(ROOT)),'sha256':inv.file_sha(v3)},
        'snapshot_v10_body':{'path':latest[ident]['body'],'sha256':latest[ident]['clean_text_sha256']},
        'canonical_original_and_candidate_current_bytes_match':True,
        'root11_explicit_selection_member':False,'current_v3_semantic_approval':False})
inv.write_json(AUDIT/'WORKING_COPY_HISTORY_INCIDENT_RECONCILIATION_V1.json',{
    'status':'POSTSTATE_PRESERVED_PRIOR_WORKING_BYTES_UNVERIFIED_INPUTS_INTACT',
    'rows':rows,'historical_snapshot_observation_tool_chunk':'50f2ac',
    'input_pins':{str(path.relative_to(ROOT)):inv.file_sha(path) for path in (manifest_path,snapshot_path,Path(__file__))},
    'original_candidate_or_existing_working_changed_by_this_producer':False,
    'cleaned_prose_authored_by_root':0,'cache3_changed':False,'goal_complete':False,'training_authorized':False})
print('2 derived working incidents reconciled; prior v2 bytes remain unverified; originals/candidates and selected v3 pins match')
