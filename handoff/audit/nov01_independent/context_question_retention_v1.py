"""Read-only CPU question-boundary audit of frozen official evaluation inputs."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import sysconfig
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).parent
sys.path.insert(0,str(ROOT))
os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
    OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',
    HF_DATASETS_OFFLINE='1',TRANSFORMERS_OFFLINE='1',USE_HUB_KERNELS='0')
from scripts.prepare_p106b_official_eval import configure_hf_cache
configure_hf_cache()
from scripts import p106b_official_mmlu as mmlu
from scripts import p106b_official_gsm8k as gsm
from scripts import diag_p106b_falcon_mmlu as falcon
from scripts import interactive_research_infer as manual
from scripts.p106b_official_lm_adapter import prepare_harness,LikelihoodCore,_adapter_type


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def forbidden(*args,**kwargs):
    raise RuntimeError('No model/weight loading or forward is allowed in this CPU audit.')


def encode(native,hf,context):
    if hf:
        value=native(context,add_special_tokens=False,return_offsets_mapping=True)
        return value['input_ids'],value['offset_mapping']
    value=native.encode(context,add_special_tokens=False)
    return value.ids,value.offsets


def measure(context,question,ids,offsets,window):
    assert question and context.endswith(question) and len(ids)==len(offsets) and ids
    question_start=len(context)-len(question)
    cut=max(0,len(ids)-window)
    retained_start=offsets[cut][0] if cut else 0
    assert 0<=retained_start<=len(context)
    lost=max(0,retained_start-question_start)
    return dict(context_tokens=len(ids),removed_context_tokens=cut,question_characters_lost=lost,
                question_fully_retained=lost==0,retained_start_character=retained_start,
                question_start_character=question_start)


def main():
    from unittest.mock import patch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    output=AUDIT/'context_question_retention_v1.json'
    assert not output.exists()
    source_sha=digest(Path(__file__))
    rows={};started=time.monotonic();code=9
    def stop(*_):raise TimeoutError('Bounded CPU audit time expired.')
    signal.signal(signal.SIGALRM,stop);signal.alarm(600)
    report=dict(schema='OFFICIAL_QUESTION_RETENTION_CPU_V1',status='STARTED',rows=rows,
        model_loads=0,model_forwards=0,gpu_runs=0,training=0,benchmark_teacher_or_train_reuse=False)
    try:
        native=manual.local_tokenizer(manual.verify_manifest())
        template,_=prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
        core=LikelihoodCore(vocab_size=native.get_vocab_size(),pad_id=native.token_to_id('<pad>'),
                            score_batch=forbidden,batch_size=4)
        native_lm=_adapter_type(template)(core=core,tokenizer=native,prefix_id=native.token_to_id('<bos>'),
            eos_id=native.token_to_id('<eos>'),provenance=dict(device='cpu',scope='QUESTION_RETENTION_ONLY'))
        profile=json.loads((ROOT/'data_cache/p106b_falcon_mmlu_v3_20261101/profile.json').read_text())
        with patch.object(AutoModelForCausalLM,'from_pretrained',side_effect=forbidden):
            hf=AutoTokenizer.from_pretrained(str(ROOT/profile['models']['path']),local_files_only=True)
            assert hf.is_fast
            hf_lm=falcon.tokenizer_only(hf)
            for shots in (0,5):
                tasks,_,_=mmlu.load_tasks(shots)
                for family,tokenizer,lm,is_hf in [('tiny',native,native_lm,False),('falcon',hf,hf_lm,True)]:
                    name=family+'_mmlu'+str(shots)
                    current=dict(total=0,context_clipped=0,question_clipped=0,example_or_header_only_clipped=0,
                        removed_context_tokens=0,maximum_question_chars_lost=0,clipped_question_cases=[])
                    rows[name]=current
                    for task_name,task in tasks.items():
                        for index,doc in enumerate(task.eval_docs):
                            request=mmlu.requests(task,doc,shots,index)[0]
                            original,continuation=request.args
                            question=task.doc_to_text(doc).rstrip()
                            context=original.rstrip()
                            ids,offsets=encode(tokenizer,is_hf,context)
                            actual_context,actual_continuation=lm._encode_pair(original,continuation)
                            assert ids==actual_context and len(actual_continuation)==1
                            value=measure(context,question,ids,offsets,1024)
                            current['total']+=1
                            current['context_clipped']+=value['removed_context_tokens']>0
                            current['question_clipped']+=not value['question_fully_retained']
                            current['example_or_header_only_clipped']+=value['removed_context_tokens']>0 and value['question_fully_retained']
                            current['removed_context_tokens']+=value['removed_context_tokens']
                            current['maximum_question_chars_lost']=max(current['maximum_question_chars_lost'],value['question_characters_lost'])
                            if not value['question_fully_retained']:
                                current['clipped_question_cases'].append(dict(subject=doc['subject'],doc_id=index,**value))
                    assert current['total']==14042
                    print(json.dumps(dict(event='MMLU_RETENTION_COMPLETE',name=name,counts={k:v for k,v in current.items() if k!='clipped_question_cases'})),flush=True)
            task,_=gsm.load_task()
            task.build_all_requests(limit=None,rank=0,world_size=1,cache_requests=False,rewrite_requests_cache=False,
                system_instruction=None,apply_chat_template=False,fewshot_as_multiturn=False)
            profile_path=ROOT/'data_cache/p106b_gsm8k_official_v1_20261101/profile_v2.json'
            fixed=json.loads(profile_path.read_text())
            current=dict(total=0,context_clipped=0,question_clipped=0,examples_only_clipped=0,
                         removed_context_tokens=0,maximum_question_chars_lost=0,clipped_question_cases=[])
            rows['tiny_gsm8k5']=current
            for index,request in enumerate(task.instances):
                context,kwargs=request.args;question=task.doc_to_text(request.doc)
                ids,offsets=encode(native,False,context);case=fixed['cases'][index]
                assert len(ids)==case['original_prompt_tokens'] and len(ids[-768:])==case['kept_prompt_tokens']
                value=measure(context,question,ids,offsets,768)
                current['total']+=1;current['context_clipped']+=value['removed_context_tokens']>0
                current['question_clipped']+=not value['question_fully_retained']
                current['examples_only_clipped']+=value['removed_context_tokens']>0 and value['question_fully_retained']
                current['removed_context_tokens']+=value['removed_context_tokens']
                current['maximum_question_chars_lost']=max(current['maximum_question_chars_lost'],value['question_characters_lost'])
                if not value['question_fully_retained']:current['clipped_question_cases'].append(dict(doc_id=index,**value))
            assert current['total']==1319
            report.update(status='COMPLETE',all_context_ids_equal_actual_cpu_adapter=True,
                tokenizer_scope='EACH_MODEL_NATIVE_TOKENIZER_OFFSETS; NO_CROSS_TOKEN_ID_ASSUMPTION',
                gsm_profile_sha256=digest(profile_path),falcon_cpu_profile_source=profile['source'])
            code=0
    except Exception as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc));raise
    finally:
        signal.alarm(0)
        report.update(actual_exit=code,seconds=time.monotonic()-started,source_sha256=source_sha,
            source_unchanged=digest(Path(__file__))==source_sha,created_at=datetime.now(timezone.utc).isoformat())
        with output.open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
        assert output.stat().st_size<20_000_000
        print(json.dumps(dict(status=report['status'],actual_exit=code,seconds=report['seconds'])),flush=True)
    return code


if __name__=='__main__':raise SystemExit(main())
