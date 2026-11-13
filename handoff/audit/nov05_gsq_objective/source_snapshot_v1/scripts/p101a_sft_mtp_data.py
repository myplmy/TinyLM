"""New frozen8M SFT subset from existing public capability/teacher shards.

Only explicit public namespaces are read. No source regeneration, downloads,
protected TinyDataset, original writes or checkpoint/model loading.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import heapq
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PUBLIC=ROOT/'HF/sft_ready/p106b_capability_public_v1'
PUBLIC_SHA='774E2CBA5DAD402C24F9A70555D0F5ACC1F660BF83BAFE793BC7E4BED9727814'
TEACHER=ROOT/'HF/sft_ready/p106b_gemma_deficit_v3'
TOKENIZER=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
VERSION='P101A_SFT_MTP_CORPUS_V1'


def digest(path):
    if path.is_symlink() or not path.is_file():raise ValueError('regular input required: '+str(path))
    sha=hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda:stream.read(1<<20),b''):sha.update(part)
    return sha.hexdigest().upper()


def lineage(row):
    meta=row['meta'];lang=meta['language'];profile=meta.get('capability_profile',meta.get('task_profile'))
    root=meta.get('parent_concept_id')
    if lang not in ('ko','en') or profile not in ('qa','json','multiturn'):
        raise ValueError('explicit language/task absent')
    if not isinstance(root,str) or len(root)!=64:
        raise ValueError('original concept identity absent')
    return lang,profile,root


def conversation_identity(row):
    """Exact conversation deduplication, independent of source/lineage metadata."""
    body=json.dumps(row['messages'],ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return hashlib.sha256(body.encode()).hexdigest().upper()


class Reservoir:
    """Hash-ordered token-budget reservoir, never first-file-prefix selection."""
    def __init__(self,goal,seed=1337):
        self.goal=goal;self.seed=seed;self.items=[];self.tokens=0;self.serial=0
    def add(self,row,x_tokens,*,teacher=False):
        if x_tokens<=0 or x_tokens>1024:raise ValueError('true conversation length required')
        key=hashlib.sha256((str(self.seed)+json.dumps(row,ensure_ascii=False,sort_keys=True)).encode()).hexdigest()
        score=int(key,16);self.serial+=1
        heapq.heappush(self.items,(-score,self.serial,x_tokens,json.dumps(row,ensure_ascii=False),teacher))
        self.tokens+=x_tokens
        while self.items and self.tokens-self.items[0][2]>=self.goal:
            self.tokens-=heapq.heappop(self.items)[2]
    def rows(self):
        for _,_,mass,body,teacher in sorted(self.items,key=lambda v:-v[0]):
            yield json.loads(body),mass,teacher


def stream_rows(directory,manifest):
    from scripts.p106b_shards import verify
    verify(directory,manifest)
    for part in manifest['shards']:
        with (directory/part['path']).open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)


def prepare(destination,*,goal=8_000_000,seed=1337):
    from tokenizers import Tokenizer
    from scripts.p106b_shards import ShardWriter
    from tinylm.train.mtp_sft import encode_record,count_record
    from tinylm.data.sft import conversation_split_key
    from scripts.p106b_gemma_deficit import Quotas
    if destination.exists() or any(p.is_symlink() for p in (destination,*destination.parents)):
        raise FileExistsError('old/linked corpus preserved')
    if digest(PUBLIC/'report.json')!=PUBLIC_SHA or digest(TOKENIZER)!=TOK_SHA:
        raise ValueError('public/tokenizer immutable identity differs')
    public=json.loads((PUBLIC/'report.json').read_text(encoding='utf-8'))
    manifests={split:json.loads((PUBLIC/(split+'_shards_manifest.json')).read_text(encoding='utf-8'))
        for split in ('train','val')}
    if any(manifests[s]['concat_sha256']!=public[s+'_concat_sha256'] for s in manifests):
        raise ValueError('public split identity differs')
    tok=Tokenizer.from_file(str(TOKENIZER))
    weights={'qa':.5,'json':.25,'multiturn':.25}
    pools={(s,l,p):Reservoir(int((goal if s=='train' else goal//20)/2*w),seed)
        for s in ('train','val') for l in ('ko','en') for p,w in weights.items()}
    val_roots=set();val_prompts=set();seen=set();seen_conversations=set();rejected=Counter();teacher_sources=[]
    for row in stream_rows(PUBLIC,manifests['val']):
        lang,profile,root=lineage(row);val_roots.add(root);val_prompts.add(conversation_split_key(row))
    def consider(row,split,is_teacher=False):
        lang,profile,root=lineage(row);prompt=conversation_split_key(row)
        if split=='train' and (root in val_roots or prompt in val_prompts):
            rejected['val_root_or_prompt']+=1;return
        key=(split,lang,profile,root,prompt)
        if key in seen:rejected['duplicate_root_prompt_profile']+=1;return
        exact=(split,conversation_identity(row))
        if exact in seen_conversations:rejected['duplicate_exact_conversation']+=1;return
        seen.add(key)
        seen_conversations.add(exact)
        try:rec=encode_record(row,tok)
        except ValueError as error:rejected[str(error)]+=1;return
        pools[split,lang,profile].add(row,rec.x_tokens,teacher=is_teacher)
    for row in stream_rows(PUBLIC,manifests['val']):consider(row,'val')
    for row in stream_rows(PUBLIC,manifests['train']):consider(row,'train')
    # Read only sealed candidate manifests in the exact prior teacher namespace.
    # Unsealed batches stay untouched and are explicitly counted as unavailable.
    if TEACHER.is_dir() and not TEACHER.is_symlink():
        for directory in sorted(TEACHER.glob('batch_*')):
            report_path=directory/'report.json'
            if directory.is_symlink() or not report_path.is_file():
                rejected['unsealed_teacher_batch']+=1;continue
            report=json.loads(report_path.read_text(encoding='utf-8'))
            manifest=report.get('candidate_manifest')
            if not manifest:rejected['teacher_without_candidates']+=1;continue
            if report.get('base_report_sha256')!=PUBLIC_SHA:
                raise ValueError('teacher original public lineage differs')
            teacher_sources.append({'report':str(report_path.relative_to(ROOT)),'sha256':digest(report_path),
                'concat_sha256':manifest['concat_sha256']})
            for row in stream_rows(directory,manifest):
                root=lineage(row)[2];split=Quotas.source_split(None,root)
                if split=='val':
                    # Do not expand a validation split after training selection.
                    rejected['teacher_val_preserved_unselected']+=1;continue
                consider(row,split,True)
    destination.mkdir(parents=True,exist_ok=False)
    counts=Counter();tokens=Counter();targets=Counter();families=Counter();teacher_tokens=Counter()
    horizon_counts=Counter();concepts={s:set() for s in ('train','val')}
    writers={s:ShardWriter(destination,s) for s in ('train','val')}
    for (split,lang,profile),pool in pools.items():
        for row,mass,is_teacher in pool.rows():
            rec=encode_record(row,tok)
            concepts[split].add(lineage(row)[2])
            row['meta'].update(mtp_subset=VERSION,mtp_split=split)
            writers[split].append(row);lane=split+':'+lang+':'+profile
            counts[lane]+=1;tokens[lane]+=mass;targets[lane]+=rec.targets
            families[split+':'+lang+':'+row['meta'].get('source_family','UNSPECIFIED')]+=mass
            if is_teacher:teacher_tokens[lane]+=mass
            for h,c in count_record(rec).items():horizon_counts[split+':'+str(h)]+=c
    manifests_out={s:w.close(lineage={'schema':VERSION,'public_report_sha256':PUBLIC_SHA}) for s,w in writers.items()}
    deficits={':'.join(k):max(0,p.goal-p.tokens) for k,p in pools.items()}
    ready=not any(deficits.values())
    report=dict(schema=VERSION,status='CORPUS_READY' if ready else 'CORPUS_INCOMPLETE',
        goal_unique_train_x_tokens=goal,epochs=4,seed=seed,public_report_sha256=PUBLIC_SHA,
        tokenizer_sha256=TOK_SHA,source_manifests={s:manifests[s]['concat_sha256'] for s in manifests},
        teacher_sources=teacher_sources,manifests=manifests_out,rows=dict(counts),x_tokens=dict(tokens),
        assistant_targets=dict(targets),horizon_targets=dict(horizon_counts),family_tokens=dict(families),
        teacher_x_tokens=dict(teacher_tokens),deficits=deficits,rejections=dict(rejected),
        unique_original_concepts={s:len(v) for s,v in concepts.items()},
        unique_mass_scope='exact unique serialized conversations, not every QA variant a new concept',
        actual_unique_train_x_tokens=sum(v for k,v in tokens.items() if k.startswith('train:')),
        target_processed_x_tokens=4*sum(v for k,v in tokens.items() if k.startswith('train:')),
        formal_train_ready=False,semantic_quality='PSEUDO_UNVERIFIED',
        initialization_scope='same corpus for scratch/parent x NTP/MTP; learned weights are not source data',
        source_cap_scope='inherited original public selection; actual8M family shares disclosed, not new25%cap proof',
        source_split='prior public val excluded by both original root and normalized prompt')
    body=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if len(body.encode())>20_000_000:raise ValueError('20MB report contract')
    with (destination/'report.json').open('x',encoding='utf-8') as stream:stream.write(body)
    return report
