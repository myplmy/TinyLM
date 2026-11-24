"""Pinned COMPS/entity AST, native phrase processing and independent rank audit.

Only existing official files are read by load_official. No model or network is
opened here. The original causal scorer/ranking functions are unchanged.
"""
from __future__ import annotations
import ast
from collections import Counter,defaultdict
import hashlib,json,math
from pathlib import Path
from types import SimpleNamespace,MethodType
from scripts import p106b_babylm_causal as prior

TASKS=('comps','entity_tracking')

def load_official(directory,torch,*,device='cpu'):
    namespace,proof=prior.load_official(directory,torch,device=device)
    directory=Path(directory);extra={}
    for filename,names in (('read_files.py',('decode_comps','decode_entity_tracking')),
                           ('dataset.py',('__getitem__',))):
        path=directory/filename;raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest().upper()!=prior.FILES[filename][0]:
            raise ValueError('same official source bytes required before extra AST selection')
        tree=ast.parse(raw.decode('utf-8'));nodes=[]
        for name in names:
            if name=='__getitem__':
                candidates=[node for owner in tree.body if isinstance(owner,ast.ClassDef)
                    and owner.name=='CompletionRankingDataset' for node in owner.body
                    if isinstance(node,ast.FunctionDef) and node.name==name]
            else:candidates=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name]
            if len(candidates)!=1 or candidates[0].decorator_list:
                raise ValueError('exact single undecorated official AST node required')
            nodes.append(candidates[0])
        module=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',
            names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[]))
        exec(compile(module,str(path),'exec'),namespace)
        extra[filename]={node.name:dict(start_line=node.lineno,end_line=node.end_lineno,
            ast_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest().upper()) for node in nodes}
    proof.update(extra_unchanged_AST_nodes=extra,task_scope=TASKS,
        original_constructor_not_called=True,original_package_import=False)
    return namespace,proof

def decode(official,task,raw,filename):
    if task not in TASKS:raise ValueError('only preregistered local COMPS/entity tasks')
    value=official['decode_'+task](raw,Path(filename))
    records=[value] if task=='comps' else value
    for row in records:
        count=len(row['sentences'])
        if (count<2 or count>64 or count!=len(row['completions']) or count!=len(row['prefixes'])
                or row['label']!=0 or not isinstance(row['UID'],str)
                or any(not isinstance(text,str) or not text for text in row['sentences'])):
            raise ValueError('complete original candidate count/label/UID/text required')
    return records

def processed_item(official,processor,decoded):
    holder=SimpleNamespace(backend='causal',processor=processor,data=[decoded])
    holder.process_causal_sentences=MethodType(official['process_causal_sentences'],holder)
    item=official['__getitem__'](holder,0)
    tensors=item[1]
    for i in range(len(decoded['sentences'])):
        prefix='sentence_'+str(i)
        tokens,mask,attention=(tensors[prefix+ending] for ending in ('_tokens','_phrase_mask','_attn_mask'))
        if (tokens.ndim!=1 or mask.shape!=tokens.shape or attention.shape!=tokens.shape
                or not bool(mask[1:].sum()>0) or len(tokens)-1>1024):
            raise ValueError('nonempty original phrase targets and full1024 native input required')
    if item[0]['sentences']!=decoded['sentences'] or item[2]!=decoded['label'] or item[4]!=decoded['UID']:
        raise ValueError('original getitem candidate/target/UID changed')
    return item

def contiguous_batches(records,*,size=8):
    if type(size)is not int or not 1<=size<=8:raise ValueError('bounded batch1..8 required')
    pending=[];count=None
    for record in records:
        choices=len(record['decoded']['sentences'])
        if pending and (choices!=count or len(pending)==size):
            yield pending;pending=[]
        pending.append(record);count=choices
    if pending:yield pending

class RankAudit:
    """Observe original exact-tie rank/UID/predictions; keep source order."""
    def __init__(self,official,torch,*,task,sink=None):
        if task not in TASKS:raise ValueError('declared task required')
        self.official,self.torch,self.task,self.sink=official,torch,task,sink
        self.original=official['rank_and_evaluate']
        self.by_uid=defaultdict(lambda:dict(total=0,correct=0))
        self.rows=self.ties=0;self.uniform_correct=0.
        self.prediction_hashes={};self.predictions=None;self.batch_records=None;self.batch_items=None
    def __enter__(self):self.official['rank_and_evaluate']=self.call;return self
    def __exit__(self,*args):self.official['rank_and_evaluate']=self.original
    def set_batch(self,records,items):
        if len(records)!=len(items) or not records:raise ValueError('whole current source batch required')
        self.batch_records,self.batch_items=records,items
    def call(self,args,stats,probabilities,raw,labels,metadatas,uids,predictions):
        torch=self.torch
        if (args.task!=self.task or args.images_path is not None or args.save_predictions is not True
                or set(probabilities)!={1.} or not 2<=len(probabilities[1.])<=64
                or str(torch.get_default_device())!='cpu' or self.batch_records is None
                or len(self.batch_records)!=len(raw) or not len(raw)==len(labels)==len(metadatas)==len(uids)):
            raise ValueError('exact native candidate/task/current batch rank contract required')
        n=len(probabilities[1.])
        if any(p.device.type!='cpu' or p.dtype!=torch.float32 or p.shape!=(len(raw),)
                or not bool(torch.isfinite(p).all()) for p in probabilities[1.]):
            raise ValueError('finite original CPU FP32 score vector per candidate required')
        before_rng=torch.get_rng_state().clone()
        before_stats={key:{name:dict(counter) for name,counter in value.items()} for key,value in stats[1.].items()}
        before_lengths={uid:len(values) for uid,values in predictions[1.].items()}
        self.original(args,stats,probabilities,raw,labels,metadatas,uids,predictions)
        after_rng=torch.get_rng_state().clone();torch.set_rng_state(before_rng)
        events=[];changes=defaultdict(lambda:dict(total=Counter(),correct=Counter()))
        try:
            for i,(sentence,label,metadata,uid) in enumerate(zip(raw,labels,metadatas,uids)):
                if label!=0 or metadata['UID']!=uid or len(sentence['sentences'])!=n:
                    raise ValueError('original label0/candidate count/UID must be preserved')
                scores=[float(p[i]) for p in probabilities[1.]];maximum=max(scores)
                ties=[j for j,value in enumerate(scores) if value==maximum]
                chosen=ties[int(torch.randint(len(ties),(1,)))] if len(ties)>1 else ties[0]
                for key,value in metadata.items():
                    changes[key]['total'][value]+=1;changes[key]['correct'][value]+=int(chosen==label)
                item=self.batch_items[i]
                native=[dict(ids=item[1]['sentence_'+str(j)+'_tokens'].tolist(),
                    phrase_mask=item[1]['sentence_'+str(j)+'_phrase_mask'].tolist()) for j in range(n)]
                events.append(dict(index=self.rows+i,source=self.batch_records[i]['trace'],task=self.task,uid=uid,
                    label=label,chosen=chosen,scores=scores,exact_tie=len(ties)>1,candidate_count=n,
                    raw=sentence,native_inputs=native,rule='OFFICIAL_RAW_PHRASE_SUM;EXACT_TIE_CPU_RNG_NO_EPSILON'))
            if not torch.equal(torch.get_rng_state(),after_rng):raise ValueError('original exact-tie RNG replay differs')
        finally:torch.set_rng_state(after_rng)
        for key,change in changes.items():
            for name in ('total','correct'):
                if Counter(stats[1.][key][name])!=Counter(before_stats[key][name])+change[name]:
                    raise ValueError('independent original metadata Counter differs')
        used=Counter()
        for event in events:
            uid=event['uid'];offset=before_lengths.get(uid,0)+used[uid];used[uid]+=1
            field='sentences' if self.task=='comps' else 'completions'
            expected=dict(id=uid+'_'+str(offset),pred=event['raw'][field][event['chosen']])
            if predictions[1.][uid][offset]!=expected:raise ValueError('original prediction/string/UID index differs')
            self.prediction_hashes.setdefault(uid,hashlib.sha256()).update(
                json.dumps(expected,ensure_ascii=False,sort_keys=True,allow_nan=False).encode())
            self.by_uid[uid]['total']+=1;self.by_uid[uid]['correct']+=int(event['chosen']==0)
            self.ties+=int(event['exact_tie']);self.uniform_correct+=1/event['candidate_count']
            if self.sink:self.sink(event)
        self.predictions=predictions[1.];self.rows+=len(events)
    def summary(self,average,*,expected_by_uid):
        if {uid:value['total'] for uid,value in self.by_uid.items()}!=expected_by_uid:
            raise ValueError('whole original decoded UID denominators differ')
        if self.predictions is None or set(self.predictions)!=set(self.prediction_hashes):
            raise ValueError('final official prediction UID coverage differs')
        for uid,expected in self.prediction_hashes.items():
            actual=hashlib.sha256()
            for record in self.predictions[uid]:actual.update(json.dumps(record,ensure_ascii=False,sort_keys=True,allow_nan=False).encode())
            if actual.digest()!=expected.digest():raise ValueError('final prediction prefix/suffix/hash differs')
        macro=math.fsum(100*value['correct']/value['total'] for value in self.by_uid.values())/len(self.by_uid)
        if not math.isclose(macro,average,abs_tol=1e-10,rel_tol=1e-12):raise ValueError('official UID macro differs')
        correct=sum(value['correct'] for value in self.by_uid.values())
        return dict(rows=self.rows,uids=len(self.by_uid),correct=correct,micro_percent=100*correct/self.rows,
            UID_macro_percent=macro,by_UID=dict(self.by_uid),exact_ties=self.ties,
            uniform_expectation_percent=100*self.uniform_correct/self.rows,
            label_order='OFFICIAL_LABEL0_GOOD_FIRST;ALWAYS_FIRST100_PERCENT_IS_LABEL_LEAKAGE_NOT_BASELINE',
            prediction_audit='ORIGINAL_RANK_RNG_AND_METADATA_COUNTER_PLUS_ALL_PREDICTION_DIGESTS',
            quality_claim='FROZEN_MODEL_TASK_SCORE_ONLY;NO_NEW_TRAINING_OR_GENERAL_KOREAN_CLAIM')
