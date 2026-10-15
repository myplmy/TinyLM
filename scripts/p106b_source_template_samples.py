"""Hash-selected source/template packets, not online semantic screening."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter,defaultdict
import hashlib
import json
FAMILIES=('NQ-Open','HotpotQA','Dolly-v2','Flan-Coqa')
PER_GROUP=8
MAX_ROW_BYTES=250000
MAX_PACKET_BYTES=64*2**20


def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest().upper()


def family(raw):
    if not isinstance(raw,str):return None
    result=raw[:-4] if raw.endswith(' (T)') else raw
    return result if result in FAMILIES else None


class Sampler:
    def __init__(self):self.groups=defaultdict(Counter);self.samples={};self.rejections=Counter()

    def add(self,row,language,spec):
        f=family(row.get('dataset_name'))
        if f is None:return
        if language not in ('ko','en') or type(row.get('id')) is not int:raise ValueError('declared language and producer integer id required')
        template=row.get('template_id');group=f'{language}:{f}:template={template}'
        self.groups[group].update(raw_rows=1,empty_or_nontext=int(any(not isinstance(row.get(k),str) or not row[k].strip() for k in ('inputs','targets'))))
        identity=dict(language=language,family=f,template=template,raw_id=row['id']);rank=sha(identity)
        payload=dict(sample_id=rank,group=group,producer_identity=identity,original=row,source_spec=spec,
            semantic_review='NOT_RUN',world_truth='NOT_REVIEWED',training_admission='NOT_DECIDED')
        size=len(json.dumps(payload,ensure_ascii=False).encode())
        if size>MAX_ROW_BYTES:self.rejections['sample_row_bytes_cap']+=1;return
        pool=self.samples.setdefault(group,{})
        if rank in pool and pool[rank]['original']!=row:raise ValueError('same sampled producer ID with different original')
        pool[rank]=payload
        if len(pool)>PER_GROUP:del pool[max(pool)]

    def rows(self):
        used=0
        for group in sorted(self.samples):
            for rank,value in sorted(self.samples[group].items()):
                size=len(json.dumps(value,ensure_ascii=False).encode())
                if used+size>MAX_PACKET_BYTES:self.rejections['global_packet_bytes_cap']+=1;continue
                used+=size;yield value

    def counts(self):return {k:dict(v) for k,v in sorted(self.groups.items())}
