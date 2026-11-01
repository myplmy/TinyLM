"""독립 sum-CE/목적별 분모의 실제 AdamW 갱신 대조. CPU fixture만 사용한다."""
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import torch
import torch.nn.functional as F
from scripts.test_p107_adaptive_training import make
from tinylm.train.hybrid_mntp import causal_batch,mntp_batch,uniform_mntp_selection

torch.set_num_threads(1)
trainer=make('uniform')
before=trainer.state_dict()
reference=copy.deepcopy(trainer.model)
optimizer=torch.optim.AdamW(reference.parameters(),lr=.001)
generator=torch.Generator().set_state(before['uniform_rng'])
source=copy.deepcopy(trainer.source)
batches=[]
for i,(tokens,docs) in enumerate(source.next_update()):
    if i<2:
        batch=causal_batch(tokens,docs,vocab_size=64);kind='causal'
    else:
        selected=uniform_mntp_selection(tokens,docs,vocab_size=64,probability=.5,generator=generator)
        batch=mntp_batch(tokens,docs,selected,vocab_size=64);kind='masked'
    batches.append((batch,kind))
totals={kind:sum(int((b.targets!=-100).sum()) for b,k in batches if k==kind)
        for kind in ('causal','masked')}
torch.set_rng_state(before['rng']['torch'])
direct_loss=0.
for batch,kind in batches:
    logits=reference(batch.inputs,attention_mask=batch.attention_mask)
    summed=F.cross_entropy(logits.reshape(-1,64),batch.targets.reshape(-1),reduction='sum',ignore_index=-100)
    # 독립식은 먼저 token 평균을 만들지 않고 목적별 sum CE를 직접 정규화한다.
    value=summed*(.5/totals[kind])
    direct_loss+=float(value.detach());value.backward()
torch.nn.utils.clip_grad_norm_(reference.parameters(),1.,error_if_nonfinite=True)
optimizer.step()
torch.set_rng_state(before['rng']['torch'])
observed=trainer.update()
diffs={name:float((param-reference.state_dict()[name]).abs().max())
       for name,param in trainer.model.state_dict().items()}
# FP32의 나눗셈/곱셈 순서 차이만 허용한다. 결과를 보고 문턱을 바꾸지 않는다.
assert abs(direct_loss-observed['loss'])<1e-6
assert max(diffs.values())<1e-7
assert torch.equal(generator.get_state(),trainer.uniform_rng.get_state())
assert observed['causal_targets']==totals['causal'] and observed['masked_targets']==totals['masked']
data=dict(status='PASS',kind='CPU_INDEPENDENT_SUM_CE_UPDATE_ORACLE',quality_claim=False,
          direct_loss=direct_loss,observed_loss=observed['loss'],parameter_max_abs_diff=diffs,
          fixed_loss_atol=1e-6,fixed_parameter_atol=1e-7,target_counts=totals,
          source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())
p=Path(__file__).with_name('p107_independent_update_oracle_v1.json')
with p.open('x',encoding='utf-8') as stream:stream.write(json.dumps(data,indent=2)+chr(10))
print(json.dumps(data))
