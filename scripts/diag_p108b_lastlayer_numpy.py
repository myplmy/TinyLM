"""Independent NumPy arithmetic from immutable CPU payload and raw captures."""
import json
import math
import numpy as np
import torch
from scripts import diag_p108b_lastlayer_forecast as study
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as tensor_tools


def run():
    p=study.study.read(study.PROFILE);r=study.study.read(study.OUT/'report.json')
    if r['status']!='LASTLAYER_CAUSAL_FORECAST_COMPLETE' or not r['original_core_restored']:
        raise ValueError('closed original-restored native observation required')
    checkpoint=study.ROOT/'runs/ckpt/m100s10_ko-en_broad4_p106b_native595_broad_v1_s1337_float.pt'
    if manual.file_sha(checkpoint)!=p['origin']['checkpoint_sha256']:raise ValueError('exact original CPU payload required')
    payload=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True);state=payload['model']
    cfg=payload['cfg']
    if cfg['n_coda']!=2 or cfg['n_prelude']+cfg['n_middle']+cfg['n_coda']!=14:
        raise ValueError('confirmed final coda mapping required')
    weight=state['coda_mlps.1.down_proj.weight'];gate=float(state['layers.13.gates'][1]);eps=cfg['norm_eps']
    arm=study.frozen.arm(p['selected']);ref=arm['packets'][0];packet=study.frozen.packet_loader(ref)
    if tensor_tools.tensor_sha(weight)!=ref['before_weight_sha256']:raise ValueError('actual native last matrix owner differs')
    physical=packet['after'].numpy().astype('float64')-weight.numpy().astype('float64')
    embedding=state['emb.weight'].numpy().astype('float64');up=state['emb_up.weight'].numpy().astype('float64')
    scale=state['norm_f_scale'].numpy().astype('float64');manifest=study.study.read(study.OUT/'PREDICTIONS_BEFORE_EDITED_FORWARD_v1.json')
    checks=[]
    for native,pin in zip(r['rows'],manifest['pins']):
        if native['id']!=pin['id'] or native['position']!=pin['position']:raise ValueError('same frozen prediction order')
        def load(reference):
            path=study.ROOT/reference['path']
            if manual.file_sha(path)!=reference['sha256']or path.stat().st_size>=20_000_000:
                raise ValueError('small exact raw vector capture required')
            with np.load(path,allow_pickle=False)as s:return {k:s[k].copy()for k in s.files}
        before=load(pin['packet']);actual=load(native['actual_packet'])
        if not np.array_equal(before['original_key'],actual['actual_key']):raise ValueError('fixed-prefix key changed')
        h=before['original_residual'].astype('float64');key=before['original_key'].astype('float64')
        d=gate*(physical@key);h2=h+d;energy=np.mean(h*h)+eps
        exact=((h2/math.sqrt(np.mean(h2*h2)+eps))*scale)@up@embedding.T
        derivative=(d-h*np.mean(h*d)/energy)/math.sqrt(energy)
        linear=((h/math.sqrt(energy)+derivative)*scale)@up@embedding.T
        observed=actual['actual_logits'].astype('float64')
        error=exact-observed;delta=float(np.linalg.norm(observed-before['original_logits']))
        checks.append(dict(id=native['id'],position=native['position'],
            raw_shift_max_error=float(np.max(np.abs(d-before['raw_shift']))),
            exact_logit_rmse=float(np.sqrt(np.mean(error*error))),exact_max_logit_error=float(np.max(np.abs(error))),
            exact_argmax=bool(np.argmax(exact)==np.argmax(observed)),linear_argmax=bool(np.argmax(linear)==np.argmax(observed)),
            exact_response_relative_error=float(np.linalg.norm(error))/max(delta,1e-30)))
    result=dict(schema='P108B_LASTLAYER_INDEPENDENT_NUMPY_V1',checkpoint_sha256=manual.file_sha(checkpoint),
        native_report_sha256=manual.file_sha(study.OUT/'report.json'),cases=len(checks),rows=checks,
        exact_argmax_matches=sum(x['exact_argmax']for x in checks),linear_argmax_matches=sum(x['linear_argmax']for x in checks),
        mean_exact_rmse=float(np.mean([x['exact_logit_rmse']for x in checks])),
        max_exact_logit_error=max(x['exact_max_logit_error']for x in checks),
        checkpoint_payload_reads=1,module_construction=0,gpu_calls=0,checkpoint_writes=0,
        method='NumPy FP64 original CPU payload matrices/gate/epsilon and raw original keys/residuals;predict actual edited native logits;no stored predicted logits used as ground truth',
        checkpoint_unchanged=manual.file_sha(checkpoint)==p['origin']['checkpoint_sha256'])
    library.write_new(study.ROOT/'handoff/audit/nov16_pm_p108b/LASTLAYER_INDEPENDENT_NUMPY_v1.json',result)
    print(json.dumps({k:v for k,v in result.items()if k!='rows'}))


if __name__=='__main__':run()
