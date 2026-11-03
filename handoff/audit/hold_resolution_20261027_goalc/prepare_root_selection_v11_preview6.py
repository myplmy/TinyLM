"""Bind five Luna corrections after root's actual date/field context review."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW5.json'
snapshot_path=inv.BASE/'remaining_birth_full_counter_v1_snapshots/v17/complete.json'
document=inv.cache.read(source);snapshot=inv.cache.read(snapshot_path)
assert not snapshot['errors']
fixes={'expanded_train:'+str(n) for n in [824834,183863,45295,121135,727409]}
reviews={}
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT/shard['path'])==shard['sha256']
    reviews.update({r['id']:r for r in inv.cache.read(ROOT/shard['path']) if r['id'] in fixes})
assert set(reviews)==fixes
norm=lambda s: re.sub(r'\s+','',s)
patches=[]
for row in document['rows']:
    if row['id'] not in fixes:continue
    choice=row['selected'];review=reviews[row['id']]
    assert review.get('body') and not review.get('error')
    assert inv.file_sha(ROOT/choice['body'])==choice['clean_text_sha256']
    assert inv.file_sha(ROOT/review['body'])==review['clean_text_sha256']
    assert inv.file_sha(ROOT/review['review']['path'])==review['review']['sha256']
    before=(ROOT/choice['body']).read_text(encoding='utf-8')
    after=(ROOT/review['body']).read_text(encoding='utf-8')
    number=row['id'].split(':')[1]
    assert before!=after
    if number=='824834':
        assert norm(before.replace('참고 자료','',1))==norm(after)
    elif number=='183863':
        assert norm(before).replace('1월21일','1월21일사망',1)==norm(after)
    elif number=='121135':
        assert norm(before).replace("1866년'제너럴셔먼호사건'의와중에죽음.","1866년9월2일경'제너럴셔먼호사건'의와중에죽음.",1)==norm(after)
    else:
        assert norm(chr(10).join(before.splitlines()[1:]))==norm(chr(10).join(after.splitlines()[1:]))
        if number=='45295':
            assert '전남' in after.splitlines()[0] and '출생' in after.splitlines()[0]
            assert '1950년10월13일' in norm(after.splitlines()[0]) and '사망' in after.splitlines()[0]
        elif number=='727409':
            assert '1020년이전' in norm(after.splitlines()[0])
            assert '1063년9월11일이전에사망' in norm(after.splitlines()[0])
    patches.append(dict(id=row['id'],before_body=dict(path=choice['body'],sha256=choice['clean_text_sha256']),
        after_body=dict(path=review['body'],sha256=review['clean_text_sha256']),review=review['review'],
        nonwhitespace_changes_limited_to_root_requested_correction=True))
    choice.update(body=review['body'],clean_text_sha256=review['clean_text_sha256'],
        review=review['review'],author_output=review.get('author_output'),root_approved=False)
    row['root_approved']=False
assert len(patches)==5
document.update(status='COMPLETED_COHORT_EXACT_CHOICES_WITH_FIVE_ROOT_CONTEXT_CORRECTIONS',
    root_followup_corrections=patches,runtime_and_numeric_guard_closure='NOT_RUN_ON_THIS_PREVIEW')
for path in [source,snapshot_path,Path(__file__),AUDIT/'ROOT11_QUALIFIED_DATE_DIAGNOSTICS_V1.json',
        AUDIT/'ROOT11_STATED_QUANTITY_DIAGNOSTICS_V1.json']:
    document['input_pins'][str(path.relative_to(ROOT))]=inv.file_sha(path)
out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
payload=(json.dumps(document,ensure_ascii=False,indent=2)+chr(10)).encode()
assert len(payload)<20_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(sources=document['source_ids'],corrected_ids=sorted(fixes),bytes=len(payload))))
