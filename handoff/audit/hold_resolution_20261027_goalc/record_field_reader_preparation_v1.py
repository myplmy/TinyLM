"""Pin observed successful preparation and scan only its new file-size scopes."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source_path=inv.BASE/'remaining_field_title_readers_v1/complete.json'
links_path=AUDIT/'REMAINING_FIELD_TITLE_READING_CONNECTIONS_V1.json'
source=inv.cache.read(source_path)
links=inv.cache.read(links_path)
assert source['sources']==links['sources']==18237 and len(source['pages'])==len(links['pages'])==36
assert links['counts']['actual_fixed_wrapper_exit_zero']==36
assert links['counts']['actual_other_role_source_rejected']==36
seen=set()
files=0
largest=0
for page in source['pages']:
    path=ROOT/page['path']
    assert inv.file_sha(path)==page['sha256']
    rows=inv.cache.read(path)['rows']
    ids={row['id'] for row in rows}
    assert len(ids)==page['sources'] and not (ids&seen)
    seen.update(ids)
    directories=[inv.BASE/page['group']]+[
        inv.BASE/'agents'/role/page['group'] for role in page['assignments']]
    for directory in directories:
        for target in directory.rglob('*'):
            assert not target.is_symlink()
            if target.is_file():
                size=target.stat().st_size
                assert 0<size<20_000_000
                files+=1
                largest=max(largest,size)
assert len(seen)==18237
names=['prepare_remaining_field_title_readers_v1.py',
       'prepare_remaining_field_title_identity_and_controls_v1.py',Path(__file__).name]
result=dict(status='OBSERVED_PREPARATION_EXIT_ZERO_ALL_FIELD_INPUTS_READY_NOT_READ',
    process_exit_observations=[
        dict(program=names[0],exit_code=0,tool_result_chunk='cef422'),
        dict(program=names[1],exit_code=0,tool_result_chunk='fb818a')],
    observation_method='OBSERVED_EXEC_TOOL_COMPLETION_NOT_REEXECUTED',seconds='NOT_MEASURED',
    unique_sources=18237,occurrences=29659,pages=36,cross_page_duplicate_sources=0,
    reading_connection_counts=links['counts'],new_file_size_check=dict(files=files,largest_bytes=largest,limit_exclusive=20_000_000),
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path)
        for path in [source_path,links_path,*[AUDIT/name for name in names]]},
    cleaned_prose_authored_by_root=0,protected_parent_bodies_opened=0,
    content_review_complete=False,cache_admitted=0,goal_complete=False,training_authorized=False)
output=AUDIT/'REMAINING_FIELD_TITLE_READER_PREPARATION_VERIFIED_V1.json'
assert not output.exists()
inv.write_json(output,result)
print(json.dumps(dict(sources=18237,pages=36,files=files,largest_bytes=largest,cache_admitted=0)))
