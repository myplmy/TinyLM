"""User-only trained-student NTP/off versus verified MTP2/3/4 + head precision."""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import time
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def run(args,corpus,evidence,metadata):
    import torch
    from tokenizers import Tokenizer
    from scripts.diag_p101a_sft_mtp import ARMS,checkpoint,report_path,write
    from scripts import p101a_sft_mtp_data as data
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from scripts.p106b_repeat4_gate import PROBES
    from tinylm.infer.generate import load_model,sample
    from tinylm.chat.serialize import serialize
    from scripts.p106b_shards import ShardWriter,verify
    if not args.arm.endswith('_mtp'):raise ValueError('inference needs a trained MTP arm')
    report=json.loads(report_path(evidence,args.arm).read_text())
    path=checkpoint(args.tag,args.arm)
    if (report.get('status')!='SFT_MTP_TRAINED_EVAL_PENDING' or not report.get('checkpoint_saved')
            or data.digest(path)!=report.get('checkpoint_sha256')):
        raise FileNotFoundError('exact completed trained MTP checkpoint required')
    target=evidence/('infer_'+args.arm)
    if target.exists():raise FileExistsError('prior inference preserved')
    target.mkdir(parents=True,exist_ok=False)
    tok=Tokenizer.from_file(str(data.TOKENIZER))
    if data.digest(data.TOKENIZER)!=data.TOK_SHA:raise ValueError('tokenizer changed')
    writer=ShardWriter(target,'answers')
    records=[];started=time.perf_counter();status='STARTED';rc=9
    try:
        idle_before_gpu()
        with wall_limit(args.max_wall_sec):
            base,cfg,_=load_model(ckpt_path=path,device='cuda',mtp_heads=4)
            saved={f'mtp_up{h}':getattr(base,f'mtp_up{h}').detach().cpu().clone() for h in (2,3,4)}
            stops=[tok.encode('<|im_end|>').ids]
            references={}
            profiles=[(1,'off')]+[(k,d) for d in ('fp32','fp16') for k in (2,3,4)]
            for k,precision in profiles:
                base.detach_mtp_heads()
                if k>1:
                    dtype=torch.float32 if precision=='fp32' else torch.float16
                    selected=tuple(range(2,k+1))
                    base.attach_mtp_heads(selected,{f'mtp_up{h}':saved[f'mtp_up{h}'].to(dtype) for h in selected})
                torch.cuda.reset_peak_memory_stats()
                for ident,question in PROBES:
                    prompt=serialize({'messages':[{'role':'user','content':question}]},'chatml',add_generation_prompt=True)
                    torch.cuda.synchronize();begin=time.perf_counter()
                    text,generation=sample(base,cfg,tok,prompt,max_new=64,temperature=0.,top_k=1,
                        device='cuda',use_cache=True,logits_last_only=True,return_metadata=True,
                        stop_token_sequences=stops,mtp_tokens=k)
                    torch.cuda.synchronize();seconds=time.perf_counter()-begin
                    if k==1:references[ident]=(text,generation['finish_reason'],generation['generated_tokens'])
                    equivalent=references[ident]==(text,generation['finish_reason'],generation['generated_tokens'])
                    row=dict(id=ident,question=question,total_prediction_tokens=k,head_precision=precision,
                        raw_full_text=text,generation=generation,seconds=seconds,equivalent_to_ntp=equivalent,
                        head_tensor_bytes=base.mtp_head_bytes(),
                        torch_peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                        torch_peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                        semantic_quality='MANUAL_RAW_REVIEW_REQUIRED')
                    writer.append(row);records.append({key:value for key,value in row.items() if key!='raw_full_text'})
                    print('[MTP_INFER_ANSWER] '+json.dumps(row,ensure_ascii=False),flush=True)
            rc=0 if all(r['equivalent_to_ntp'] for r in records) else 8
            status='VERIFIED_INFERENCE_MEASURED' if rc==0 else 'GPU_NUMERIC_PARITY_NEGATIVE'
    except BaseException as error:
        if isinstance(error,KeyboardInterrupt):rc=130;status='INTERRUPTED'
        else:rc=9;status='EXECUTION_ERROR'
        records.append({'error_type':type(error).__name__,'reason':str(error)[:1200]})
    finally:
        manifest=writer.close(lineage={'checkpoint_sha256':report['checkpoint_sha256']}) if writer._total_rows else None
        if manifest:verify(target,manifest)
        write(target/'report.json',dict(metadata,status=status,returncode=rc,arm=args.arm,
            model_loading='MEASURED' if records and 'error_type' not in records[0] else 'UNKNOWN_RUNTIME_PROGRESS',
            trained_checkpoint_sha256=report['checkpoint_sha256'],records=records,raw_manifest=manifest,
            whole_wall_sec=time.perf_counter()-started,student_training='NOT_RUN_IN_INFERENCE_GATE',
            inference_scope='greedy/cache-on fixed64 tokens; sampling/long-context/packed CPU speed NOT_RUN',
            quality_scope='same main model outputs; does not repair wrong NTP answers'))
    return rc
