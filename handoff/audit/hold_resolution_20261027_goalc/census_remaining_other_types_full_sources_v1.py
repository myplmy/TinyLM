"""Enumerate all unresolved other-type sources and immutable bounded review pages."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

SOURCE=inv.BASE/'remaining_unassigned_all_sources_v1'
OUT=inv.BASE/'remaining_other_types_full_sources_v1'
assert not OUT.exists()
source_path=SOURCE/'complete.json';source=inv.cache.read(source_path)
reason='UNRESOLVED_FIELD_OR_TITLE'
inv.verify(SOURCE/'rows',source['rows'])
rows=[r for r in inv.cache.rows(SOURCE/'rows',source['rows']) if reason not in r['previous_reasons']]
assert len(rows)==source['counts']['queued_unique']-source['pending_reasons_unique'][reason]==50162
assert len({r['id'] for r in rows})==len({r['original_text_sha256'] for r in rows})==50162
pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in [source_path,Path(__file__)]}
writer=inv.ShardWriter(OUT/'rows','all_other_type_sources',limit=19_999_999)
for row in rows:
    row['named_review_strata']=['ENTIRE_REMAINING_OTHER_TYPES',*row['previous_reasons']]
    writer.append(row)
manifest=writer.close(lineage=dict(input_pins=pins))
pages=[];covered=[]
for index,offset in enumerate(range(0,len(rows),512),1):
    page=rows[offset:offset+512]
    directory=OUT/'pages'/('page_'+str(index).zfill(3));directory.mkdir(parents=True)
    path=directory/'complete.json'
    value=dict(status='BOUNDED_PAGE_OF_ENTIRE_TYPE_NOT_SAMPLING_OR_ADMISSION',rows=page,
        counts=dict(queued_unique=len(page),queued_positions=sum(r['occurrences'] for r in page)),
        page=index,parent_total_sources=50162,parent_total_pages=98,
        input_pins=pins,original_bodies_opened=False,goal_complete=False,training_authorized=False)
    payload=(json.dumps(value,ensure_ascii=False,indent=2)+chr(10)).encode()
    assert len(payload)<20_000_000
    with path.open('xb') as f:f.write(payload)
    pages.append(dict(page=index,path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),
        sources=len(page),positions=value['counts']['queued_positions']))
    covered.extend(r['id'] for r in page)
assert covered==[r['id'] for r in rows] and len(pages)==98
result=dict(status='ENTIRE_OTHER_TYPES_PAGINATED_NOT_REVIEWED',
    counts=dict(queued_unique=50162,queued_positions=sum(r['occurrences'] for r in rows)),
    rows=manifest,pages=pages,input_pins=pins,page_capacity=512,
    meaning='512 limits one review-page artifact, never the authorized total work. All98 pages remain required.',
    original_bodies_opened=False,cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(OUT/'complete.json',result)
print(json.dumps(dict(counts=result['counts'],pages=len(pages),original_bodies_opened=False)))
