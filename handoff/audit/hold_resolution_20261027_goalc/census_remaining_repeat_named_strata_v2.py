"""Count all unresolved repeats and select entire named review strata, not admissions."""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE=inv.BASE
output=BASE/'repeat_remaining_named_strata_v2'
inv.require(not output.exists(),'new immutable named strata census required')
source=BASE/'repeat_context_shape_census_v1'
shape_path=source/'complete.json'
shape=inv.cache.read(shape_path)
root_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10.json'
root=inv.cache.read(root_path)
protected_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
protected=inv.cache.read(protected_path)
blocked_hashes=set(protected['restricted_hashes'])
blocked_ids=set(protected['restricted_ids'])
selected={row['original_text_sha256'] for row in root['rows']}
inv.verify(source/'rows',shape['rows'])
headings='''Introduction|Background|History|Overview|Description|Method|Methods|Materials|Materials and Methods|Results|Discussion|Conclusion|Conclusions|Summary|Applications|Examples|Properties|Characteristics|Taxonomy|Distribution|Habitat|Behavior|Behaviour|Ecology|Life cycle|Symptoms|Causes|Diagnosis|Treatment|Prevention|Epidemiology|Etymology|Development|Reception|Legacy|Biography|Early life|Career|Education|Personal life|Awards|Works|Discography|Track listing|개요|역사|설명|생애|일생|생애 및 경력|경력|활동|학력|용도|응용|이용|분포|서식지|생태|특징|성질|구조|작용|연구|개발|평가|수상|업적|출연|작품|저서|음반|결론|방법|결과|토론|배경'''
known_headings={value.casefold() for value in headings.split('|')}
ui=re.compile(r'(?i)^(?:back to top|like\s*liked by [0-9]+ (?:person|people)|continue reading below|(?:-[ \t]*)?share this|map and directions|no exact matches found[.]?|about the author|add to favorites|leave a reply|read more)$')
wiki=re.compile(r'^[|!][ \t]*(?:[-+]|(?:scope|style|align|valign|rowspan|colspan)[ \t]*=)')
writer=inv.ShardWriter(output/'rows','candidates',limit=19_999_999)
counts,groups=Counter(),Counter()
started=time.monotonic()
for row in inv.cache.rows(source/'rows',shape['rows']):
    counts['whole_repeat_unique']+=1
    if row['original_text_sha256'] in selected:
        counts['already_exact_root_selected']+=1
        continue
    counts['remaining_repeat_unique']+=1
    counts['remaining_repeat_positions']+=row['occurrences']
    inv.require(row['id'] not in blocked_ids and row['original_text_sha256'] not in blocked_hashes,
                'restricted source must stay metadata-only and unassigned')
    details=row['repeated_lines']
    full=[item['preview'].strip() for item in details if item['characters']==len(item['preview'])]
    tags=[]
    if row['bucket']=='ONLY_TYPED_BYLINES':
        tags.append('ENTIRE_REPEATED_BYLINE_SHAPE_BUCKET')
    if any(ui.fullmatch(value) for value in full):
        tags.append('REPEATED_EXPLICIT_PAGE_UI_STRING_REQUIRES_CONTEXT')
    if full and len(full)==len(details) and all(value.casefold() in known_headings for value in full):
        tags.append('ALL_REPEATED_LINES_ARE_NAMED_SECTION_LABELS')
    if full and len(full)==len(details) and all(wiki.match(value) for value in full):
        tags.append('ALL_REPEATED_LINES_ARE_WIKI_CELL_OR_LAYOUT_ROLES')
    if not tags:
        counts['outside_current_named_strata']+=1
        continue
    writer.append(dict(row,named_review_strata=tags,root_approved=False,cache_admitted=False))
    groups.update(tags)
    counts['selected_unique']+=1
    counts['selected_positions']+=row['occurrences']
inv.require(counts['whole_repeat_unique']==21891 and counts['remaining_repeat_unique']==21727,
            'whole unresolved repeated-source conservation differs')
pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [shape_path,root_path,protected_path,
      AUDIT/'REPEAT_REMAINING_FULL_STRATA_SCOPE_V2.md',Path(__file__)]}
manifest=writer.close(lineage=dict(input_pins=pins))
result=dict(status='WHOLE_REMAINING_REPEAT_CENSUS_AND_ENTIRE_NAMED_REVIEW_STRATA_NOT_ADMISSION',
    counts=dict(counts),groups=dict(groups),rows=manifest,input_pins=pins,
    native_source_rerun=False,body_changed=0,root_approved=False,cache_admitted=0,
    goal_complete=False,training_authorized=False,seconds=time.monotonic()-started)
inv.write_json(output/'complete.json',result)
print(json.dumps({key:result[key] for key in ['status','counts','groups','seconds']}),flush=True)
