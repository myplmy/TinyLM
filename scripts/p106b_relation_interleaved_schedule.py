"""Reorder the same source-root views; never change question/answer content."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
from scripts import p106b_relation_fields as factory


def schedules(rows):
    original=[rows['train'+str(v)] for v in range(4)];n=0
    for row in original[0]:
        if row['meta']['kind']!='fictional_relation_fields':break
        n+=1
    if not n or n%2 or len({len(v) for v in original})!=1:raise ValueError('paired-language fictional prefix and equal full row lengths required')
    if any(any(r['meta']['kind']=='fictional_relation_fields' for r in source[n:]) for source in original):raise ValueError('fiction must be a complete leading prefix')
    output={};pointers={};balance={}
    for epoch in range(4):
        selected=[];refs=[];counts=Counter()
        for position in range(n):
            index=position//2;lang=('ko','en')[position%2];view=(index+epoch)%4
            row=original[view][position];m=row['meta']
            if m['producer_graph']['index']!=index or m['language']!=lang or m['view']!=view:raise ValueError('declared root/language/view alignment required')
            selected.append(row);refs.append(dict(source_view=view,source_row_index=position,row_sha256=factory.sha(row)));counts[str(view)]+=1
        for position,row in enumerate(original[epoch][n:],n):
            selected.append(row);refs.append(dict(source_view=epoch,source_row_index=position,row_sha256=factory.sha(row)))
        output['train'+str(epoch)]=selected;pointers['train'+str(epoch)]=refs;balance[str(epoch)]=dict(counts)
    before=Counter(factory.sha(r) for source in original for r in source)
    after=Counter(factory.sha(r) for source in output.values() for r in source)
    if before!=after:raise ValueError('global complete canonical-row multiset differs')
    proof=dict(fiction_rows_per_epoch=n,total_rows_per_epoch=len(original[0]),per_epoch_view_rows=balance,
        whole_row_multiset_sha256=factory.sha(sorted(before.items())),canonical_record_visit_multiset_equal=True,
        teacher_code_replay_unchanged=True,logical_root_passes=4,views_per_root=4)
    return output,pointers,proof
