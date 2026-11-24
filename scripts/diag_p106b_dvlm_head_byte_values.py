"""CPU-only head tensor means/VJP; no pretrained model construction/inference."""
from __future__ import annotations
import argparse,gc,hashlib,json,os,struct,sys,time,weakref
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.diag_p106b_dvlm_head_map import digest,read,write
from scripts.p106b_shards import verify
from scripts import p106b_dvlm_head as head_core
BASE=ROOT/'test_result/evidence/p106b_dvlm_head_byte_values_v1_20261117'
MAPPING=ROOT/'test_result/evidence/p106b_dvlm_head_bytes_v1_20261117'
NATIVE=ROOT/'test_result/evidence/p106b_dvlm_native_closure_v3_20261117'
WEIGHT=ROOT/'HF/models--Qwen3-0.6B-Base/model.safetensors'
KEY='model.embed_tokens.weight'
SOURCES=('scripts/diag_p106b_dvlm_head_byte_values.py','scripts/p106b_dvlm_head.py',
 'scripts/test_p106b_dvlm_head.py','scripts/p106b_alm_bytes.py','scripts/p106b_dvlm_pts.py',
 'scripts/diag_p106b_dvlm_head_map.py','scripts/p106b_shards.py')
def matrix():
    report=read(MAPPING/'actual/report.json');verify(MAPPING/'actual',report['manifest'])
    if report['returncode']!=0 or report['changed_rows']!=205:raise ValueError('closed full byte map required')
    mapping=dict(records=[],complete=True,student_vocab_size=32768)
    for shard in report['manifest']['shards']:
        mapping['records'].extend(json.loads(line)for line in(MAPPING/'actual'/shard['path']).read_text(encoding='utf-8').splitlines())
    if len(mapping['records'])!=32768:raise ValueError('whole new32768 mapping required')
    return mapping
def header():
    with WEIGHT.open('rb')as f:
        size=struct.unpack('<Q',f.read(8))[0]
        if size>20_000_000:raise ValueError('bounded safetensors header required')
        values=json.loads(f.read(size))
    selected=values[KEY]
    if selected['dtype']!='BF16' or selected['shape']!=[151936,1024]:raise ValueError('exact original head shape/dtype required')
    return selected
def prepare():
    mapping=matrix();source=read(NATIVE/'profile.json');native=read(NATIVE/'actual/report.json')
    expected=source['assets']['files']['model.safetensors']['sha256']
    if digest(WEIGHT)!=expected:raise ValueError('original safetensors file changed')
    contract=read(ROOT/'handoff/audit/research_20261117_01a1e647/CPU_NEW_METHOD_CONTRACTS_v1.json')
    for name in ('scripts/p106b_dvlm_head.py','scripts/test_p106b_dvlm_head.py','scripts/p106b_alm_bytes.py'):
        if digest(ROOT/name)!=contract['source_SHA256'][name]:raise ValueError('inherited six-contract source changed')
    independent=ROOT/'handoff/audit/research_20261117_01a1e647/HEAD_BYTE_MAPPING_INDEPENDENT_v1.json'
    if not read(independent)['passed']:raise ValueError('full byte independent closure required')
    config=read(WEIGHT.parent/'config.json')
    if config['vocab_size']!=151936 or config['hidden_size']!=1024 or config['tie_word_embeddings']is not True:
        raise ValueError('original native tying/config required')
    inputs={str(p.relative_to(ROOT)):digest(p)for p in (WEIGHT,WEIGHT.parent/'config.json',MAPPING/'profile.json',
        MAPPING/'actual/report.json',NATIVE/'profile.json',NATIVE/'actual/report.json',independent)}
    for part in read(MAPPING/'actual/report.json')['manifest']['shards']:
        p=MAPPING/'actual'/part['path'];inputs[str(p.relative_to(ROOT))]=digest(p)
    bytes_ids=[r['student_id']for r in mapping['records']if r['method']=='MEAN_NATIVE_BYTE_BPE'][:4]
    shared_ids=[r['student_id']for r in mapping['records']if r['method']=='SHARED_NATIVE_PIECE'][:2]
    targets=bytes_ids+shared_ids+[0,32767]
    profile=dict(user_directive=158,UTC=datetime.now(timezone.utc).isoformat(),sources={n:digest(ROOT/n)for n in SOURCES},
        inputs=inputs,safetensors_header=header(),exact_tensor_key=KEY,
        expected_FP32_head_SHA256=native['output_head_weight_sha256'],teacher_shape=[151936,1024],new_head_shape=[32768,1024],
        hidden_basis_columns=[0,1,2,17,127,255,511,1023],hidden_basis_scales=[.125,.25]*4,targets=targets,
        inherited_head_CPU_contracts=6,byte_mapping_contracts=5,atol=1e-5,rtol=1e-4,
        maximum_seconds=300,minimum_available_RAM_bytes=4*1024**3,model_loads=0,GPU_calls=0,
        new_head_weight_files=0,optimizer_updates=0,training_steps=0)
    BASE.mkdir(exist_ok=False);write(BASE/'profile.json',profile);print('HEAD_CPU_PROFILE',digest(BASE/'profile.json'),flush=True)
def tensor_sha(torch,tensor):
    value=tensor.detach().contiguous()
    return hashlib.sha256(value.view(-1).view(torch.uint8).numpy().tobytes()).hexdigest().upper()
def actual():
    p=read(BASE/'profile.json');start=time.perf_counter();directory=BASE/'actual';directory.mkdir(exist_ok=False)
    report=dict(status='STARTED',returncode=1,user_directive=158,PID=os.getpid(),model_loads=0,GPU_calls=0,
        source_tensor_reads=0,new_head_weight_files=0,optimizer_updates=0,training_steps=0,checkpoint_writes=0,quality_claim=False)
    import psutil,torch
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    if torch.cuda.is_initialized():raise ValueError('CPU process unexpectedly initialized CUDA')
    teacher=head=hidden=None;references=[]
    def check():
        if time.perf_counter()-start>p['maximum_seconds'] or datetime.now(timezone.utc)>=datetime.fromisoformat('2026-11-17T16:40:00+09:00'):
            raise TimeoutError('CPU tensor wall/clock cap')
        if p['sources']!={n:digest(ROOT/n)for n in SOURCES}:raise ValueError('current CPU source changed')
        for name,sha in p['inputs'].items():
            if digest(ROOT/name)!=sha:raise ValueError('pinned CPU tensor input changed')
    try:
        check();report['RSS_entry']=psutil.Process().memory_info().rss
        if psutil.virtual_memory().available<p['minimum_available_RAM_bytes']:raise ValueError('4GiB available RAM required')
        mapping=matrix();from safetensors import safe_open
        with safe_open(str(WEIGHT),framework='pt',device='cpu')as f:
            teacher=f.get_tensor(KEY).to(dtype=torch.float32).contiguous().requires_grad_()
        report['source_tensor_reads']=1
        if list(teacher.shape)!=p['teacher_shape'] or tensor_sha(torch,teacher)!=p['expected_FP32_head_SHA256']:
            raise ValueError('selected head tensor differs from original observed exact FP32 native head')
        references.append(weakref.ref(teacher));head=head_core.initialize_head(torch,teacher,mapping,chunk_rows=128)
        references.append(weakref.ref(head));before=tensor_sha(torch,head)
        oracle=head_core.independent_row_oracle(torch,head,teacher,mapping,atol=p['atol'],rtol=p['rtol'])
        report['all_rows_FP64_mean_oracle']=oracle
        if not oracle['passed']:raise ValueError('full32768 independent row oracle failed')
        print('ALL_ROWS_MEAN_ORACLE',oracle,flush=True)
        hidden=torch.zeros(8,1024,dtype=torch.float32)
        for i,(column,scale)in enumerate(zip(p['hidden_basis_columns'],p['hidden_basis_scales'])):hidden[i,column]=scale
        hidden.requires_grad_();references.append(weakref.ref(hidden));hidden_before=tensor_sha(torch,hidden)
        probe=head_core.head_gradient_probe(torch,head,hidden,p['targets']);report['full_vocab_head_probe']=probe
        # Independent FP64 analytical derivative of mean full-vocabulary CE.
        with torch.no_grad():
            features=hidden.detach().double();values=head.detach().double();scores=features@values.T
            targets=torch.tensor(p['targets'],dtype=torch.long)
            ce64=torch.nn.functional.cross_entropy(scores,targets,reduction='mean')
            probabilities=scores.softmax(-1);probabilities[torch.arange(8),targets]-=1
            expected=(probabilities.T@features/8).to(torch.float32)
            observed=head.grad.detach();close=torch.isclose(observed,expected,atol=p['atol'],rtol=p['rtol'])
            report['independent_FP64_VJP']=dict(passed=bool(close.all()) and math_close(probe['CE_mean'],float(ce64),p),
                rows=32768,columns=1024,violating_elements=int((~close).sum()),max_abs=float((observed-expected).abs().max()),
                CE_mean_FP64=float(ce64),atol=p['atol'],rtol=p['rtol'])
            report['head_gradient_sha256']=tensor_sha(torch,observed)
            del features,values,scores,targets,ce64,probabilities,expected,observed,close
        if not probe['finite'] or not probe['gradient_nonzero'] or not report['independent_FP64_VJP']['passed']:
            raise ValueError('full head finite/nonzero/independent gradient failed')
        if teacher.grad is not None or hidden.grad is not None:raise ValueError('teacher or detached hidden gradient exists')
        if (tensor_sha(torch,head)!=before or tensor_sha(torch,hidden)!=hidden_before
                or tensor_sha(torch,teacher)!=p['expected_FP32_head_SHA256']):raise ValueError('original teacher/hidden/new head values changed')
        report.update(status='CPU_FULL_HEAD_MEAN_VJP_COMPLETE',returncode=0,new_head_sha256=before,
            teacher_FP32_SHA256=p['expected_FP32_head_SHA256'],teacher_FP32_bytes=teacher.numel()*teacher.element_size(),
            new_head_FP32_bytes=head.numel()*head.element_size(),gradient_FP32_bytes=head.grad.numel()*head.grad.element_size(),
            teacher_and_hidden_grad_absent=True,all_values_unchanged=True,RSS_after_probe=psutil.Process().memory_info().rss)
        check();report['source_inputs_unchanged']=True
    except BaseException as exc:report.update(status='CPU_HEAD_ERROR',returncode=1,error=dict(type=type(exc).__name__,message=str(exc)))
    finally:
        teacher=head=hidden=None;gc.collect()
        report['owned_tensor_references_released']=all(ref()is None for ref in references)
        report['CUDA_initialized']=torch.cuda.is_initialized()
        report['RSS_exit']=psutil.Process().memory_info().rss
        if not report['owned_tensor_references_released'] or report['CUDA_initialized']:
            report.update(status='CPU_HEAD_RELEASE_ERROR',returncode=9)
        report['wall_seconds']=time.perf_counter()-start
        write(directory/'report.json',report)
    print('HEAD_CPU_TERMINAL',report['status'],report['returncode'],report['wall_seconds'],flush=True)
    return report['returncode']
def math_close(left,right,p):
    import math
    return math.isclose(left,right,abs_tol=p['atol'],rel_tol=p['rtol'])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','actual'));args=parser.parse_args()
    if args.action=='prepare':prepare();return 0
    return actual()
if __name__=='__main__':raise SystemExit(main())
