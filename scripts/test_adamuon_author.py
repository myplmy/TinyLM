"""Independent author-factor, BF16 resume and optional CPU Gloo2 contracts."""
from __future__ import annotations
import copy,io,json,sys,time,unittest
from datetime import timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import torch
from tinylm.train.adamuon_author import AdaMuonAuthor,SCHEMA
from scripts.p005b_adamuon_precision import local_step,NS_ORDERS,TAILS

def bits_equal(a,b):
    return a.dtype==b.dtype and a.shape==b.shape and torch.equal(
        a.detach().contiguous().view(torch.uint8),b.detach().contiguous().view(torch.uint8))

def gradient(shape,step,index=0):
    return torch.cos(torch.arange(torch.tensor(shape).prod().item(),dtype=torch.float32)*.7+step+index).reshape(shape)

def independent(reference,grad):
    result=local_step(reference['weight'],grad,reference['momentum'],reference['variance'],
        ns_order=NS_ORDERS[1],tail=TAILS[1],beta=.8,lr=.01,weight_decay=.1)
    return dict(weight=result['weight'],momentum=result['momentum'],variance=result['variance'])

def initial_reference(p):
    return dict(weight=p.detach().clone(),momentum=torch.zeros_like(p),
        variance=torch.zeros_like(p,dtype=torch.bfloat16))

class AuthorSingleContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        if torch.cuda.is_initialized():raise ValueError('CPU contracts must not initialize CUDA')

    def test_independent_author_factor_raw_bits_for_two_nesterov_branches(self):
        for shape in ((3,7),(7,3),(4,4)):
            for nesterov in (False,True):
                p=torch.nn.Parameter(torch.arange(shape[0]*shape[1],dtype=torch.float32).reshape(shape)/100)
                reference=initial_reference(p)
                opt=AdaMuonAuthor([p],lr=.01,momentum=.8,weight_decay=.1,nesterov=nesterov)
                for step in range(5):
                    grad=gradient(shape,step);p.grad=grad.clone()
                    result=local_step(reference['weight'],grad,reference['momentum'],reference['variance'],
                        ns_order=NS_ORDERS[1],tail=TAILS[1],beta=.8,lr=.01,weight_decay=.1,nesterov=nesterov)
                    reference={key:result[key]for key in ('weight','momentum','variance')}
                    opt.step()
                    self.assertTrue(bits_equal(p,reference['weight']))
                    self.assertTrue(bits_equal(opt.state[p]['momentum_buffer'],reference['momentum']))
                    self.assertTrue(bits_equal(opt.state[p]['v_buffer'],reference['variance'].flatten()))
                    self.assertTrue(bits_equal(p.grad,grad))

    def test_none_gradient_is_rejected_before_any_state_or_weight_write(self):
        ps=[torch.nn.Parameter(torch.ones(2,3)),torch.nn.Parameter(torch.ones(3,2))]
        opt=AdaMuonAuthor(ps);ps[0].grad=torch.ones_like(ps[0])
        before=[p.detach().clone()for p in ps]
        with self.assertRaisesRegex(ValueError,'None gradient'):opt.step()
        self.assertFalse(opt.state)
        self.assertTrue(all(bits_equal(p,b)for p,b in zip(ps,before)))

    def test_exact_state_and_distinct_size_scratch_bytes(self):
        ps=[torch.nn.Parameter(torch.ones(s))for s in ((2,3),(3,2),(2,2))]
        opt=AdaMuonAuthor(ps)
        for p in ps:p.grad=gradient(p.shape,0)
        opt.step()
        self.assertEqual(sum(t.untyped_storage().nbytes()for state in opt.state.values()for t in state.values()),6*16)
        self.assertEqual(opt.scratch_bytes,2*(6+4))
        self.assertEqual(opt.state_dict()['author_contract']['schema'],SCHEMA)
        for group in opt.state_dict()['param_groups']:
            self.assertNotIn('update_buffer',group);self.assertNotIn('update_buffer_views',group)

    def test_serialized_resume_preserves_bf16_flat_V_and_next_step(self):
        p=torch.nn.Parameter(torch.arange(15,dtype=torch.float32).reshape(3,5)/10)
        opt=AdaMuonAuthor([p],lr=.01,momentum=.8,weight_decay=.1)
        for step in range(2):p.grad=gradient(p.shape,step);opt.step()
        stream=io.BytesIO();torch.save(opt.state_dict(),stream);stream.seek(0)
        saved=torch.load(stream,weights_only=True)
        frozen=copy.deepcopy(saved)
        q=torch.nn.Parameter(p.detach().clone());resumed=AdaMuonAuthor([q])
        resumed.load_state_dict(saved)
        self.assertEqual(resumed.state[q]['v_buffer'].dtype,torch.bfloat16)
        self.assertEqual(resumed.state[q]['v_buffer'].shape,(15,))
        for step in range(2,5):
            p.grad=gradient(p.shape,step);q.grad=p.grad.clone();opt.step();resumed.step()
            self.assertTrue(bits_equal(p,q))
            for name in opt.state[p]:self.assertTrue(bits_equal(opt.state[p][name],resumed.state[q][name]))
        for key,state in saved['state'].items():
            for name,tensor in state.items():self.assertTrue(bits_equal(tensor,frozen['state'][key][name]))

    def test_resume_rejects_wrong_method_rank_dtype_and_orphan(self):
        p=torch.nn.Parameter(torch.ones(2,3));p.grad=torch.ones_like(p)
        opt=AdaMuonAuthor([p]);opt.step();saved=copy.deepcopy(opt.state_dict())
        bad=copy.deepcopy(saved);bad['author_contract']['rank']=1
        with self.assertRaisesRegex(ValueError,'rank/world/topology'):opt.load_state_dict(bad)
        bad=copy.deepcopy(saved);next(iter(bad['state'].values()))['v_buffer']=torch.ones(6)
        with self.assertRaisesRegex(ValueError,'dtype'):opt.load_state_dict(bad)
        bad=copy.deepcopy(saved);bad['state'][99]=copy.deepcopy(next(iter(bad['state'].values())))
        with self.assertRaisesRegex(ValueError,'orphan'):opt.load_state_dict(bad)
        for key,state in opt.state_dict()['state'].items():
            for name,tensor in state.items():self.assertTrue(bits_equal(tensor,saved['state'][key][name]))

    def test_zero_gradient_is_finite_zero_without_history(self):
        p=torch.nn.Parameter(torch.ones(2,3));p.grad=torch.zeros_like(p)
        opt=AdaMuonAuthor([p],weight_decay=0);opt.step()
        self.assertTrue(bits_equal(p,torch.ones_like(p)))
        self.assertTrue(bool((opt.state[p]['v_buffer']==0).all()))

    def test_explicit_4d_author_scale_and_flat_state(self):
        shape=(2,2,3,3);p=torch.nn.Parameter(torch.zeros(shape));p.grad=gradient(shape,0)
        opt=AdaMuonAuthor([p],lr=.01,weight_decay=0,momentum=.8);opt.step()
        update=-p.detach()/.01
        expected_rms=.2*(min(shape)*max(shape)/p.numel())**.5
        self.assertAlmostEqual(float(update.square().mean().sqrt()),expected_rms,delta=.002)
        self.assertEqual(opt.state[p]['v_buffer'].shape,(p.numel(),))
        self.assertEqual(opt.state[p]['v_buffer'].dtype,torch.bfloat16)

    def test_fixed_topology_and_fp32_master_validation(self):
        p=torch.nn.Parameter(torch.ones(2,3));opt=AdaMuonAuthor([p])
        with self.assertRaisesRegex(ValueError,'topology is fixed'):opt.add_param_group({'params':[torch.nn.Parameter(torch.ones(2,2))]})
        with self.assertRaises(ValueError):AdaMuonAuthor([torch.nn.Parameter(torch.ones(2,3,dtype=torch.bfloat16))])
        with self.assertRaises(ValueError):AdaMuonAuthor([p,p])
        with self.assertRaises(ValueError):AdaMuonAuthor([p],eps=1e-100)
        with self.assertRaises(ValueError):AdaMuonAuthor([p],world_size=2)

    def test_nonfinite_gradient_rejection_preserves_all_existing_states(self):
        ps=[torch.nn.Parameter(torch.ones(s))for s in ((2,3),(3,2))]
        opt=AdaMuonAuthor(ps)
        for p in ps:p.grad=torch.ones_like(p)
        opt.step();before=copy.deepcopy(opt.state_dict());weights=[p.detach().clone()for p in ps]
        ps[1].grad[0,0]=float('nan')
        with self.assertRaisesRegex(ValueError,'finite differs'):opt.step()
        self.assertTrue(all(bits_equal(a,b)for a,b in zip(ps,weights)))
        after=opt.state_dict()
        for key,state in before['state'].items():
            for name,tensor in state.items():self.assertTrue(bits_equal(tensor,after['state'][key][name]))

def gloo_worker(rank,directory):
    import torch.distributed as dist
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    out=Path(directory);status='ERROR';record=dict(rank=rank,world_size=2)
    try:
        dist.init_process_group('gloo',init_method='file://'+str(out/'rendezvous'),rank=rank,world_size=2,
            timeout=timedelta(seconds=20))
        ps=[torch.nn.Parameter(torch.arange(torch.tensor(s).prod().item(),dtype=torch.float32).reshape(s)/100)
            for s in ((2,3),(3,2),(1,6),(2,2))]
        references=[initial_reference(p)for p in ps]
        opt=AdaMuonAuthor(ps,lr=.01,momentum=.8,weight_decay=.1,rank=rank,world_size=2)
        checked=0;resume=False
        for step in range(4):
            for index,p in enumerate(ps):
                p.grad=gradient(p.shape,step,index)
                references[index]=independent(references[index],p.grad)
            opt.step()
            for p,reference in zip(ps,references):
                if not bits_equal(p,reference['weight']):raise ValueError('distributed independent factor raw bits differ')
                gathered=[torch.empty_like(p)for _ in range(2)]
                dist.all_gather(gathered,p.detach())
                if not all(bits_equal(p,value)for value in gathered):raise ValueError('rank weight bytes differ')
                checked+=1
            if step==1:
                state=copy.deepcopy(opt.state_dict())
                ps=[torch.nn.Parameter(p.detach().clone())for p in ps]
                opt=AdaMuonAuthor(ps,rank=rank,world_size=2)
                opt.load_state_dict(state);resume=True
                if any(s['v_buffer'].dtype!=torch.bfloat16 for s in opt.state.values()):
                    raise ValueError('distributed resume V dtype differs')
        weights=[p.detach().clone()for p in ps];before=copy.deepcopy(opt.state_dict())
        for p in ps:p.grad=torch.ones_like(p)
        if rank==0:ps[0].grad=None
        try:opt.step()
        except ValueError as exc:
            if 'None gradient' not in str(exc):raise
            rejected=True
        else:raise ValueError('one-rank None was accepted')
        if not all(bits_equal(p,w)for p,w in zip(ps,weights)):raise ValueError('None fault changed weights')
        after=opt.state_dict()
        for key,state in before['state'].items():
            for name,tensor in state.items():
                if not bits_equal(tensor,after['state'][key][name]):raise ValueError('None fault changed state')
        if torch.cuda.is_initialized():raise ValueError('CPU Gloo unexpectedly initialized CUDA')
        record.update(status='PASS',independent_parameter_steps=checked,resume=resume,one_rank_None_rejected=rejected,
            weights_and_states_unchanged_on_None=True,scratch_bytes=opt.scratch_bytes,
            state_bytes=sum(t.untyped_storage().nbytes()for state in opt.state.values()for t in state.values()),
            owned_parameter_states=len(opt.state),CUDA_initialized=False)
        status='PASS'
    except BaseException as exc:
        record.update(status='ERROR',error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        with (out/('rank'+str(rank)+'.json')).open('x') as f:json.dump(record,f,sort_keys=True)
        if dist.is_initialized():dist.destroy_process_group()

def run_gloo(directory):
    import torch.multiprocessing as mp
    out=Path(directory).absolute();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();context=mp.spawn(gloo_worker,args=(str(out),),nprocs=2,join=False)
    try:
        while not context.join(timeout=1):
            if time.monotonic()-started>45:raise TimeoutError('owned Gloo contract 45s cap')
    finally:
        if any(p.is_alive()for p in context.processes):
            for p in context.processes:
                if p.is_alive():p.terminate()
            for p in context.processes:p.join(timeout=5)
    reports=[json.loads((out/('rank'+str(i)+'.json')).read_text())for i in range(2)]
    if any(r['status']!='PASS'for r in reports):raise ValueError('both Gloo ranks must pass')
    result=dict(schema='ADAMUON_AUTHOR_CPU_GLOO2_CONTRACT_V1',returncode=0,reports=reports,
        wall_seconds=time.monotonic()-started,model_loads=0,GPU_calls=0,training_tokens=0,
        scope='SYNTHETIC_CPU_TRANSPORT_AND_RESUME;NOT_CUDA_NCCL_OR_MODEL_QUALITY')
    with (out/'report.json').open('x') as f:json.dump(result,f,sort_keys=True)
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--gloo':
        if len(sys.argv)!=3:raise SystemExit('--gloo requires one new output directory')
        run_gloo(sys.argv[2])
    else:unittest.main()

