"""Pinned MTP teacher profile and pure benchmark contracts; no model on import."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/'HF/models--ayshinko--Ternary-Bonsai-2-27B-PTQ1_0-MTP-gguf'
MODEL=ASSET/'Bonsai-2-27B-PTQ1_0-MTP-Q8_0.gguf'
LORA=ASSET/'adapters/bonsai-abliterate-lora.gguf'
SERVER=Path('/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe/llama-server')
MODEL_SHA='4C21BFCFA7E643D32179DB409751941C5D1F7FCF188901C286E37D3913809CD1'
LORA_SHA='F1669534803D340A496015F5C45125F3437B4D13EC764F40E34488CE83967F42'
SERVER_SHA='F0321669B20397593E3AC09972BF6F4B7A0684954906565353B7CA84B4B0320F'
RUNTIME_LIBRARIES={
    'libllama-server-impl.so':'2CFB0A53563E84C08A7DB8C2BDE7F2626795C50EDEC43FBB6FEF1F06A481619F',
    'libllama.so.0.2.0':'18ABA2ECAC30DB3E33824404336892DDAB249FE0DBC7DDD85D1DCB4677210023',
    'libllama-common.so.0.2.0':'7B0EBC4E2C9E49A8FE239685ECE514BF748C7949B72946E0F72FA99FC164476A',
    'libggml-base.so.0.21.0':'AA5DEF0A17B595647EC2C166EE705DBE8F16CF8B7DAFFF0BE503A8EC890B0EC4',
    'libggml.so.0.21.0':'FFD6A736AD58E2D9407ED427252520FFBD4BCA8DD5DE467ECB2BD446A7A3D75B',
    'libggml-cuda.so':'F201092E0AE9053C6A8245B4E3D7A141BCF086A60E2F190842F6C969976DC664',
}
CONTEXT,MAX_OUTPUT,THINKING_BUDGET=32768,16384,8192
EFFORT='xhigh'
CONDITIONS={'base':(False,False),'mtp':(True,False),'lora':(False,True),'mtp_lora':(True,True)}
ORDERS={'mtp':(('base','mtp'),('mtp','base')),
        'lora':(('base','mtp_lora','mtp','lora'),('lora','mtp','mtp_lora','base'))}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*2**20),b''):h.update(chunk)
    return h.hexdigest().upper()


def text_sha(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest().upper()


def evidence_field(row,path):
    if not isinstance(path,list) or not 1<=len(path)<=12:raise ValueError('bounded JSON field path required')
    value=row
    for key in path:
        if isinstance(key,str) and 'reasoning' in key:raise ValueError('reasoning is not a final refusal answer')
        if not (isinstance(key,str) or type(key)==int and key>=0):raise ValueError('invalid JSON field component')
        value=value[key]
    if not isinstance(value,str) or not value.strip():raise ValueError('nonempty question/final answer required')
    return value


def validate_refusal_trigger(evidence,row):
    """Validate an offline human/GPT observation; never classify natural text."""
    if (evidence.get('schema')!='P106B_LORA_OBSERVED_REFUSAL_V1'
            or evidence.get('allowed_educational_request') is not True
            or evidence.get('observed_refusal') is not True
            or not evidence.get('reviewer') or not evidence.get('reason')):
        raise ValueError('reviewed refusal on allowed educational question required')
    allowed_models={MODEL_SHA,'53107F530AA52EB00912263AB1EE29BD199261C87CD7B4AD4CA1318C1FE33EE3'}
    if evidence.get('source_model_sha256') not in allowed_models:raise ValueError('Bonsai2 source identity differs')
    q=evidence_field(row,evidence.get('question_path'));a=evidence_field(row,evidence.get('answer_path'))
    if text_sha(q)!=evidence.get('question_sha256') or text_sha(a)!=evidence.get('final_sha256'):
        raise ValueError('reviewed question/final text changed')
    return {'reviewer':evidence['reviewer'],'source_model_sha256':evidence['source_model_sha256'],
            'question_sha256':text_sha(q),'final_sha256':text_sha(a),'basis':'OFFLINE_CONTEXT_REVIEW'}


def lora_refusal_gate():
    evidence_path=ROOT/'HF/sft_ready/p106b_mtp_teacher_v1/lora_trigger.json'
    if evidence_path.is_symlink() or not evidence_path.is_file():
        raise FileNotFoundError('C choice: observed educational refusal evidence absent; LoRA teacher remains HOLD')
    evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
    raw=evidence.get('source')
    if not isinstance(raw,str) or not raw.startswith('HF/sft_ready/') or '..' in Path(raw).parts:
        raise ValueError('exact public teacher shard under HF/sft_ready required')
    path=ROOT/raw
    if (path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to((ROOT/'HF/sft_ready').resolve())
            or path.stat().st_size>20_000_000 or path.suffix!='.jsonl'):
        raise ValueError('bounded non-linked source JSONL required')
    if digest(path)!=evidence.get('source_sha256'):raise ValueError('source SHA changed')
    number=evidence.get('line_number')
    if type(number)!=int or number<1:raise ValueError('one-based exact source line required')
    with path.open(encoding='utf-8') as f:
        row=next((json.loads(line) for i,line in enumerate(f,1) if i==number),None)
    if row is None:raise ValueError('source line absent')
    return {**validate_refusal_trigger(evidence,row),'evidence_sha256':digest(evidence_path),
            'source_sha256':evidence['source_sha256'],'source':raw,'line_number':number}


def gguf_metadata(stream):
    """Read at most64MiB of GGUF metadata/tensor descriptors, never weights."""
    formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
    def read(n):
        if n<0 or stream.tell()+n>64*2**20:raise ValueError('GGUF header exceeds64MiB')
        b=stream.read(n)
        if len(b)!=n:raise ValueError('truncated GGUF header')
        return b
    def number(fmt):return struct.unpack('<'+fmt,read(struct.calcsize(fmt)))[0]
    def string():
        n=number('Q')
        if n>2**24:raise ValueError('GGUF string too large')
        return read(n).decode('utf-8')
    def value(t,depth=0):
        if depth>4:raise ValueError('GGUF nesting too deep')
        if t==8:return string()
        if t==9:
            child,n=number('I'),number('Q')
            if n>2**20:raise ValueError('GGUF array too large')
            for _ in range(n):value(child,depth+1)
            return {'array_count':n,'element_type':child}
        if t not in formats:raise ValueError('unknown GGUF metadata type')
        return number(formats[t])
    if read(4)!=b'GGUF' or number('I')!=3:raise ValueError('GGUF v3 required')
    nt,nk=number('Q'),number('Q')
    if nt>100000 or nk>100000:raise ValueError('GGUF count bound')
    metadata={}
    for _ in range(nk):
        key=string();v=value(number('I'))
        if key.startswith(('general.','adapter.')) or 'nextn' in key or key.endswith('.block_count'):
            metadata[key]=v
    tensors={}
    for _ in range(nt):
        name=string();nd=number('I')
        if not 1<=nd<=4:raise ValueError('invalid tensor rank')
        dims=[number('Q') for _ in range(nd)];typ,offset=number('I'),number('Q')
        if name in tensors:raise ValueError('duplicate tensor name')
        tensors[name]={'shape':dims,'ggml_type':typ,'offset':offset}
    return {'metadata':metadata,'tensors':tensors,'header_bytes':stream.tell(),'tensor_count':nt}


def validate_layout(model,adapter):
    m,a=model['metadata'],adapter['metadata']
    if m.get('general.architecture')!='qwen35' or m.get('qwen35.nextn_predict_layers')!=1:
        raise ValueError('pinned qwen35 one-layer MTP metadata required')
    if not any('nextn.' in n for n in model['tensors']):raise ValueError('MTP tensors absent')
    if (a.get('general.architecture')!=m['general.architecture']
            or a.get('adapter.type')!='lora' or a.get('general.type')!='adapter'):
        raise ValueError('LoRA architecture/type mismatch')
    pairs={}
    for name,t in adapter['tensors'].items():
        match=re.fullmatch(r'(.+)\.lora_([ab])',name)
        if not match:raise ValueError('unknown adapter tensor suffix')
        pairs.setdefault(match[1],{})[match[2]]=t['shape']
    if not pairs:raise ValueError('empty adapter')
    for base,p in pairs.items():
        target=model['tensors'].get(base,{}).get('shape')
        if set(p)!={'a','b'} or not target or len(target)!=2:raise ValueError('adapter target/pair absent')
        if len(p['a'])!=2 or len(p['b'])!=2:raise ValueError('adapter matrices required')
        # GGUF embedding LoRA stores A as(rank,vocab), unlike a Linear's(in,rank).
        match=(p['a'][1]==target[1] and p['b'][1]==target[0] and p['a'][0]==p['b'][0]
               if base=='token_embd.weight' else
               p['a'][0]==target[0] and p['b'][1]==target[1] and p['a'][1]==p['b'][0])
        if not match:
            raise ValueError('adapter dimensions mismatch')
    return {'adapter_pairs':len(pairs),'layout_compatibility':'METADATA_ONLY',
            'runtime_effects':'NOT_RUN','mtp_layers':m['qwen35.nextn_predict_layers']}


def metadata_preflight(full_hash=False):
    for p in (MODEL,LORA,SERVER):
        if p.is_symlink() or not p.is_file():raise ValueError(f'exact asset absent/linked: {p}')
    if ASSET.is_symlink() or LORA.parent.is_symlink():raise ValueError('linked asset directory')
    if MODEL.stat().st_size!=6397969728 or LORA.stat().st_size!=9682464:raise ValueError('pinned asset size changed')
    with MODEL.open('rb') as f:m=gguf_metadata(f)
    with LORA.open('rb') as f:a=gguf_metadata(f)
    layout=validate_layout(m,a)
    if digest(SERVER)!=SERVER_SHA or digest(LORA)!=LORA_SHA:raise ValueError('binary/adapter SHA changed')
    runtime={}
    for name,expected in RUNTIME_LIBRARIES.items():
        p=SERVER.parent/name
        if p.is_symlink() or not p.is_file() or digest(p)!=expected:raise ValueError('runtime library absent/changed: '+name)
        runtime[name]=expected
    if full_hash and digest(MODEL)!=MODEL_SHA:raise ValueError('model SHA changed')
    return {'model':str(MODEL.relative_to(ROOT)),'model_bytes':MODEL.stat().st_size,
            'model_sha256':MODEL_SHA,'model_hash_check':'MATCH' if full_hash else 'PINNED_PREVIOUS_READ_NOT_REHASHED',
            'adapter':str(LORA.relative_to(ROOT)),'adapter_bytes':LORA.stat().st_size,'adapter_sha256':LORA_SHA,
            'server':str(SERVER),'server_sha256':SERVER_SHA,'model_metadata':m['metadata'],
            'runtime_libraries_sha256':runtime,
            'adapter_metadata':a['metadata'],**layout,'gpu_model_execution':'NOT_RUN'}


def cases():
    """Four benign, code-authored Korean/English teacher-workload profiles."""
    values=[('qa_ko','ko',1,'컴퓨터의 RAM과 SSD의 차이를 초보자에게 두 문장으로 설명해 주세요.'),
            ('qa_en','en',1,'Explain why a leap year exists in two sentences for a beginner.'),
            ('fiction_ko','ko',2,'TRPG에서 허구의 악역을 입체적으로 만드는 방법을 설명해 주세요. 현실의 위해 행동을 권하지 않는 창작 조언으로 답하세요.'),
            ('history_en','en',2,'For a history class, explain in neutral terms why democratic institutions sometimes weaken. Give a concise educational answer, not political persuasion.')]
    return [{'id':i,'language':lang,'answers':n,'question':q,'job':{'teacher_task':'answer_given',
             'target_language':lang,'source_payload':{'question':q},'source_id':'mtpbench:'+i,
             'source_sha256':text_sha(q),'source_license':'repository-code-authored'}} for i,lang,n,q in values]


def messages(case):
    from scripts.p106b_teacher_format import teacher_prompt
    from scripts.p106b_multi_answer import multi_prompt
    return (teacher_prompt('answer_given',case['language'],case['job']['source_payload'])
            if case['answers']==1 else multi_prompt(case['job'],case['answers']))


def sampling_payload(case,seed,greedy=False):
    from scripts.diag_p106b_teacher_answer_repair import SAMPLER
    payload={**SAMPLER,'messages':messages(case),'reasoning_effort':EFFORT,'seed':seed,
             'max_tokens':MAX_OUTPUT,'thinking_budget_tokens':THINKING_BUDGET,'cache_prompt':False}
    if greedy:payload.update(temperature=0.0,top_k=1,top_p=1.0,min_p=0.0)
    return payload


def server_command(condition,port,key):
    if condition not in CONDITIONS:raise ValueError('unknown condition')
    mtp,lora=CONDITIONS[condition]
    args=[str(SERVER),'--offline','--model',str(MODEL),'--host','127.0.0.1','--port',str(port),
          '--api-key',key,'--no-webui','--parallel','1','--ctx-size',str(CONTEXT),
          '--batch-size','64','--ubatch-size','64','--threads','8','--fit','off','--no-op-offload',
          '--gpu-layers','all','--cache-ram','0','--cache-reuse','0','--no-warmup','--perf',
          '--verbosity','4','--log-colors','off','--reasoning','auto','--reasoning-budget',str(THINKING_BUDGET),
          '--spec-type','draft-mtp' if mtp else 'none','--spec-draft-n-max','2']
    if lora:args.extend(['--lora-scaled',str(LORA)+':1.0'])
    return args


def response_metrics(reply,wall_sec):
    if not math.isfinite(wall_sec) or wall_sec<=0:raise ValueError('invalid request timing')
    choices=reply.get('choices')
    if not isinstance(choices,list) or len(choices)!=1:raise ValueError('one chat completion required')
    message=choices[0].get('message',{})
    final,reasoning=message.get('content') or '',message.get('reasoning_content') or ''
    if not isinstance(final,str) or not isinstance(reasoning,str):raise ValueError('string final/reasoning required')
    tokens=reply.get('usage',{}).get('completion_tokens')
    if type(tokens)!=int or tokens<0:raise ValueError('missing/negative completion token count')
    timings=reply.get('timings',{})
    n,ms=timings.get('predicted_n'),timings.get('predicted_ms')
    decode=(n/(ms/1000) if type(n)==int and n>0 and isinstance(ms,(int,float)) and math.isfinite(ms) and ms>0 else None)
    d,accepted=timings.get('draft_n'),timings.get('draft_n_accepted')
    if not (type(d)==int and type(accepted)==int and 0<=accepted<=d):d=accepted=None
    return {'completion_tokens':tokens,'request_wall_sec':wall_sec,'completion_tok_per_sec':tokens/wall_sec,
            'decode_tokens':n if decode is not None else None,'decode_ms':ms if decode is not None else None,
            'decode_tok_per_sec':decode,'prompt_tok_per_sec':timings.get('prompt_per_second'),
            'prompt_processed_tokens':timings.get('prompt_n'),'prompt_cached_tokens':timings.get('cache_n'),
            'draft_tokens':d,'accepted_draft_tokens':accepted,'draft_acceptance':accepted/d if d else None,
            'final_text':final,'reasoning_text':reasoning,'finish_reason':choices[0].get('finish_reason'),
            'final_characters':len(final),'reasoning_characters':len(reasoning),
            'empty_final':not bool(final.strip()),
            'semantic_refusal':'NOT_REVIEWED','semantic_truth':'NOT_RUN'}


def parse_wire(reply,case):
    from scripts.p106b_teacher_format import parse_reply
    from scripts.p106b_multi_answer import parse_multi
    if case['answers']==1:
        parsed=parse_reply(reply,language=case['language'])
        ok=parsed.get('format_status')=='TAGGED_COMPLETE'
    else:
        parsed=parse_multi(reply,case['answers'],case['language']);ok=parsed.get('status')=='MULTI_FORMAT_READY'
    return {'wire_ready':ok,'wire_status':parsed.get('format_status',parsed.get('status')),
            'technical_candidate_rows':case['answers'] if ok else 0,
            'candidate_truth':'NOT_RUN'}


def summarize(records,mode):
    result={}
    for condition in sorted({c for order in ORDERS[mode] for c in order}):
        rows=[r for r in records if r.get('kind')=='response' and r['condition']==condition]
        seconds=sum(r['metrics']['request_wall_sec'] for r in rows)
        decode_rows=[r for r in rows if r['metrics']['decode_ms'] is not None]
        first={}
        for r in rows:first.setdefault(r['round'],r['id'])
        later=[r for r in rows if r['id']!=first[r['round']]]
        later_sec=sum(r['metrics']['request_wall_sec'] for r in later)
        result[condition]={'requests':len(rows),'expected_requests':8,
            'completion_tokens':sum(r['metrics']['completion_tokens'] for r in rows),
            'request_sum_sec':seconds,'completion_tok_per_sec':sum(r['metrics']['completion_tokens'] for r in rows)/seconds if seconds else None,
            'decode_timing_coverage':len(decode_rows),'decode_tok_per_sec':
                sum(r['metrics']['decode_tokens'] for r in decode_rows)/(sum(r['metrics']['decode_ms'] for r in decode_rows)/1000) if decode_rows else None,
            'first_request_per_restart':[r['metrics']['request_wall_sec'] for r in rows if r['id']==first[r['round']]],
            'later_request_count':len(later),
            'later_completion_tok_per_sec':sum(r['metrics']['completion_tokens'] for r in later)/later_sec if later_sec else None,
            'wire_ready':sum(r['wire']['wire_ready'] for r in rows),
            'technical_candidate_rows':sum(r['wire'].get('technical_candidate_rows',0) for r in rows),
            'final_wire_characters_per_sec':sum(r['metrics']['final_characters'] for r in rows)/seconds if seconds else None,
            'finish_counts':dict(Counter(r['metrics']['finish_reason'] for r in rows)),
            'refusal_rate':None,'refusal_review':'NOT_REVIEWED'}
    return result


def paired_comparisons(records,arms,mode):
    """Report both orders separately; incomplete panels never get a ratio."""
    pairs=[('base','mtp','MTP_NO_LORA')]
    if mode=='lora':pairs.extend([('base','lora','LORA_NO_MTP'),('mtp','mtp_lora','LORA_WITH_MTP'),('lora','mtp_lora','MTP_WITH_LORA')])
    result=[]
    for left,right,label in pairs:
        row={'comparison':label,'reference':left,'candidate':right,'rounds':[]}
        for ri in (0,1):
            subsets=[[r for r in records if r.get('kind')=='response' and r['round']==ri and r['condition']==c] for c in (left,right)]
            if any(len(s)!=len(cases()) for s in subsets):
                row['rounds'].append({'round':ri,'status':'INCOMPLETE_NO_RATIO'});continue
            summaries=summarize([r for subset in subsets for r in subset],mode);l,r=summaries[left],summaries[right]
            memory=[]
            for c in (left,right):
                a=next((a for a in arms if a['condition']==c and a['round']==ri and a['status']=='COMPLETE'),None)
                memory.append(a.get('memory') if a else None)
            row['rounds'].append({'round':ri,'status':'MEASURED' if l['completion_tok_per_sec'] else 'ZERO_OUTPUT_NO_THROUGHPUT_RATIO',
                'completion_throughput_ratio':r['completion_tok_per_sec']/l['completion_tok_per_sec'] if l['completion_tok_per_sec'] else None,
                'request_wall_ratio_reference_over_candidate':l['request_sum_sec']/r['request_sum_sec'],
                'decode_throughput_ratio':r['decode_tok_per_sec']/l['decode_tok_per_sec'] if l['decode_tok_per_sec'] and r['decode_tok_per_sec'] else None,
                'reference_completion_tokens':l['completion_tokens'],'candidate_completion_tokens':r['completion_tokens'],
                'gpu_increment_delta_mib':memory[1]['sampled_gpu_increment_mib']-memory[0]['sampled_gpu_increment_mib'] if all(memory) else None,
                'rss_delta_mib':memory[1]['owned_server_peak_rss_mib']-memory[0]['owned_server_peak_rss_mib'] if all(memory) else None,
                'refusal_difference':'NOT_REVIEWED'})
        result.append(row)
    return result


def validate_refusal_labels(records,labels):
    expected={r['id']:r for r in records if r.get('kind')=='response'}
    seen={};allowed={'ANSWER','REFUSAL','PARTIAL','INVALID','UNSURE'}
    for label in labels:
        ident=label.get('id')
        if ident in seen or ident not in expected:raise ValueError('unknown/duplicate refusal review id')
        r=expected[ident]
        if label.get('final_sha256')!=text_sha(r['metrics']['final_text']):raise ValueError('review answer changed')
        if label.get('label') not in allowed or not label.get('reviewer') or not label.get('reason'):
            raise ValueError('review label/reviewer/reason required')
        seen[ident]=label
    if set(seen)!=set(expected) or not seen:raise ValueError('complete nonempty review coverage required')
    out={}
    for c in {r['condition'] for r in expected.values()}:
        ls=[seen[k]['label'] for k,r in expected.items() if r['condition']==c]
        out[c]={'reviewed':len(ls),'counts':dict(Counter(ls)),
                'refusal_rate':ls.count('REFUSAL')/len(ls),'scope':'fixed benign prompt panel; not general refusal rate'}
    return out
