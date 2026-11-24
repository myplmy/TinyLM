"""Pinned BabyLM reading functions and explicit native tokenizer/trace bridge.

No original package is imported. Only three hash-verified, undecorated original
function AST nodes are compiled. Model/GPU entry belongs to the separate driver.
"""
from __future__ import annotations
import ast,copy,hashlib,json,math
from pathlib import Path
from typing import Any
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'data_cache/p106b_official_eval_tools/babylm_eval_6f825c_reading_aoa_source_20261117'
OLD=ROOT/'data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp'
READING=ROOT/'data_cache/p106b_official_eval_assets/babylm_2026_strict_8d52da9/evaluation_data/full_eval/reading/reading_data.csv'
BLOBS={'strict/evaluation_pipeline/reading/evaluation_functions.py':'ad48ad07599a561b736b777ba61177b9e0e0b9d4',
    'strict/evaluation_pipeline/reading/run.py':'f417d2ac619fd30edaf36ad468c7b34cb80e10a6'}

class ReadingHold(ValueError):pass

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def source_nodes(path,names,namespace):
    raw=Path(path).read_bytes();tree=ast.parse(raw.decode());nodes=[]
    proof={}
    for name in names:
        matches=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name]
        if len(matches)!=1 or matches[0].decorator_list:raise ValueError('exact original function required')
        node=matches[0];nodes.append(node)
        proof[name]=dict(start=node.lineno,end=node.end_lineno,AST_sha256=hashlib.sha256(
            ast.dump(node,include_attributes=False).encode()).hexdigest().upper())
    module=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[]))
    exec(compile(module,str(path),'exec'),namespace)
    return proof

def load_official(torch,*,device):
    import tinylm  # Apply project cache routing before Transformers imports.
    from transformers.utils import ModelOutput
    from scripts.diag_p106b_babylm_causal import PINNED
    old_manifest=OLD/'manifest.json'
    if sha(old_manifest)!=PINNED[str(old_manifest.relative_to(ROOT))]:raise ValueError('closed original source manifest changed')
    manifest=json.loads(old_manifest.read_text())
    util=next(row for row in manifest['files']if row['path']=='strict/evaluation_pipeline/utils.py')
    utilpath=ROOT/util['local_path']
    if sha(utilpath)!=util['sha256'].upper():raise ValueError('original get_logits source differs')
    source=ARCHIVE/'source/strict/evaluation_pipeline/reading/evaluation_functions.py'
    raw=source.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=BLOBS['strict/evaluation_pipeline/reading/evaluation_functions.py']:raise ValueError('original reading function blob differs')
    namespace=dict(torch=torch,np=np,DEVICE=device,Any=Any,ModelOutput=ModelOutput)
    proofs=dict(utils=source_nodes(utilpath,['get_logits'],namespace),
        reading=source_nodes(source,['get_p','get_p2'],namespace))
    return namespace,dict(source_sha256=sha(source),utils_sha256=sha(utilpath),functions=proofs,
        source_imported_as_package=False,original_model_loader_executed=False,device=device)

def rows():
    import pandas as pd
    frame=pd.read_csv(READING,dtype={'item':str});frame['item']=frame['item'].fillna('None')
    result=[]
    for index,row in frame.iterrows():
        current=(row['item'],row['word'])
        previous=(row['prev_item'],row['prev_word'])if isinstance(row['prev_item'],str)else None
        if any(not isinstance(x,str)or not x for pair in (current,previous)if pair is not None for x in pair):
            raise ReadingHold('original full reading context/word must be nonempty strings')
        result.append(dict(index=int(index),context=current[0],word=current[1],previous=previous))
    if len(result)!=1726:raise ValueError('original full reading denominator differs')
    return result

class NativeBatch(dict):
    def to(self,device):
        for key,value in self.items():self[key]=value.to(device)
        return self

class TokenizerBridge:
    def __init__(self,tokenizer,torch,*,native,vocab,limit=1024):
        self.tokenizer,self.torch,self.native,self.vocab,self.limit=tokenizer,torch,native,vocab,limit
        self.reset()
    def reset(self):self.prefixes=[];self.targets=[]
    def __call__(self,text,*,return_tensors=None,add_special_tokens=True):
        if not isinstance(text,str)or not text:raise ReadingHold('nonempty original tokenizer text required')
        encoded=self.tokenizer.encode(text,add_special_tokens=add_special_tokens)
        ids=list(encoded.ids)if self.native else list(encoded)
        if not ids or any(type(i)is not int or not 0<=i<self.vocab for i in ids):
            raise ReadingHold('complete native input/target IDs required')
        if return_tensors is None:
            self.targets.append(tuple(ids));return {'input_ids':ids}
        if return_tensors!='pt'or len(ids)>self.limit:raise ReadingHold('no original context cropping permitted')
        self.prefixes.append(tuple(ids))
        tensor=self.torch.tensor([ids],dtype=self.torch.long)
        return NativeBatch(input_ids=tensor,attention_mask=self.torch.ones_like(tensor))
    def decode(self,token):
        if type(token)is not int or not 0<=token<self.vocab:raise ReadingHold('native decoded piece ID required')
        text=(self.tokenizer.decode([token],skip_special_tokens=False)if self.native else self.tokenizer.decode(token))
        if not isinstance(text,str)or not text or '\ufffd'in text:
            raise ReadingHold('single native piece decoded empty or with a replacement character')
        return text

class ReadingForward:
    def __init__(self,base):self.base=base;self.capture=False;self.last_logits=[]
    def __call__(self,**inputs):
        logits=self.base(**inputs)['logits']
        if self.capture:self.last_logits.append(logits[0,-1].detach().cpu().clone())
        return (logits,)

def evaluate(namespace,forward,tokenizer,context,word):
    tokenizer.reset()
    probability,multi=namespace['get_p2'](context,word,forward,tokenizer)
    probability=float(probability)
    if not math.isfinite(probability)or not 0<probability<=1:raise ReadingHold('original word probability underflow/nonfinite')
    if len(tokenizer.prefixes)!=len(tokenizer.targets)or not tokenizer.prefixes:
        raise ValueError('each original forward must retain one target call')
    trace=[dict(prefix_ids=list(prefix),target_ids=list(target),target_id=target[0])
        for prefix,target in zip(tokenizer.prefixes,tokenizer.targets)]
    return dict(probability=probability,surprisal=-math.log(probability),multi=int(multi),
        trace=trace,native_positions=sum(len(x)for x in tokenizer.prefixes))

def CE_oracle(result,forward,torch):
    if len(result['trace'])!=len(forward.last_logits):raise ValueError('whole oracle call trace required')
    targets=torch.tensor([r['target_id']for r in result['trace']],dtype=torch.long)
    loss=float(torch.nn.functional.cross_entropy(torch.stack(forward.last_logits),targets,reduction='sum'))
    passed=math.isclose(loss,result['surprisal'],abs_tol=1e-5,rel_tol=1e-4)
    return dict(original_surprisal=result['surprisal'],independent_full_label_CE=loss,
        difference=abs(loss-result['surprisal']),passed=passed,atol=1e-5,rtol=1e-4)

class ExactPairCache:
    def __init__(self,model_identity):self.identity=model_identity;self.values={};self.hits=self.misses=0
    def get(self,identity,context,word,calculate):
        if identity!=self.identity:raise ValueError('exact reading cache cannot cross models')
        key=(context,word)
        if key in self.values:self.hits+=1;return copy.deepcopy(self.values[key]),True
        value=calculate()
        self.values[key]=copy.deepcopy(value);self.misses+=1
        return copy.deepcopy(value),False

