"""Fixed semantic-root grouping for projector calibration, never benchmark splitting."""
import re


def split_by_root(rows):
    if not rows:raise ValueError('original nonempty TRAIN rows required')
    result={'train':[],'dev':[]};seen=set();languages={'train':set(),'dev':set()}
    for row in rows:
        key=root=None
        if isinstance(row,dict):key=row.get('row_id');root=row.get('semantic_root_id')
        if (not isinstance(key,str)or not key or key in seen or not isinstance(root,str)
                or re.fullmatch('[0-9a-fA-F]{64}',root)is None or row.get('language')not in ('ko','en')):
            raise ValueError('unique original row ID, declared root SHA and language required')
        seen.add(key);fold='dev'if int(root,16)%5==0 else'train'
        result[fold].append(key);languages[fold].add(row['language'])
    if any(languages[k]!={'ko','en'}for k in result):raise ValueError('both original languages required in both root-disjoint parts')
    return result
