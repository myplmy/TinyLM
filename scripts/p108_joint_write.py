"""One multi-key covariance-preserving edit inside a fixed Frobenius ball.

Single-layer adaptation, not the full multi-layer MEMIT algorithm. All arrays
are detached CPU doubles during the solve. No model, optimizer or I/O is used.
"""
import math
import torch


def covariance(keys,*,ridge_ratio=.01):
    if not isinstance(keys,torch.Tensor) or keys.ndim!=2 or len(keys)<2 or not bool(torch.isfinite(keys).all()) or keys.requires_grad:
        raise ValueError('detached finite calibration rows required')
    if type(ridge_ratio)not in(int,float) or not math.isfinite(ridge_ratio) or ridge_ratio<=0:
        raise ValueError('positive declared ridge ratio required')
    keys=keys.cpu().double();moment=keys.T@keys/len(keys);ridge=float(moment.diagonal().mean())*ridge_ratio
    if ridge<=0:raise ValueError('nonzero calibration energy required')
    return moment+ridge*torch.eye(keys.shape[1],dtype=torch.float64),dict(samples=len(keys),width=keys.shape[1],ridge=ridge,moment_trace=float(moment.trace()))


def joint_packet(keys,values,moment,base_weight,*,relative_cap=.05):
    inputs=(keys,values,moment,base_weight)
    if (any(not isinstance(x,torch.Tensor) or x.ndim!=2 or x.requires_grad or x.dtype not in (torch.float32,torch.float64) or not bool(torch.isfinite(x).all()) for x in inputs)
            or keys.shape[1]<1 or values.shape[1]!=keys.shape[1]
            or moment.shape!=(keys.shape[0],keys.shape[0])
            or base_weight.shape!=(values.shape[0],keys.shape[0])
            or type(relative_cap)not in(int,float) or not math.isfinite(relative_cap) or not 0<relative_cap<=1):
        raise ValueError('detached finite keys/values/covariance/base shapes and fixed positive norm cap required')
    k,r,c=(x.cpu().double() for x in (keys,values,moment));w=base_weight.cpu()
    if not torch.allclose(c,c.T,atol=1e-9,rtol=1e-9):raise ValueError('symmetric covariance required')
    c=(c+c.T)/2
    if int(torch.linalg.cholesky_ex(c).info)!=0:raise ValueError('positive definite covariance required')
    weight_norm=float(w.double().norm())
    if not weight_norm:raise ValueError('nonzero original weight norm required')
    s=k@k.T+c;eigen,q=torch.linalg.eigh(s)
    if not bool(torch.isfinite(eigen).all()) or bool((eigen<=0).any()):raise ValueError('finite positive normal-matrix spectrum required')
    qtk=q.T@k;projected=r@qtk.T;squared=projected.square().sum(0)
    target=relative_cap*(1-1e-5)*weight_norm
    def norm(lam):return float((squared/(eigen+lam).square()).sum().sqrt())
    unconstrained=norm(0.);lam=0.;steps=0
    if unconstrained>target:
        lo=0.;hi=max(1.,float(eigen[-1]))
        for _ in range(200):
            if norm(hi)<=target:break
            hi*=2
        else:raise RuntimeError('finite norm multiplier bracket unavailable')
        for _ in range(96):
            mid=(lo+hi)/2
            if norm(mid)>target:lo=mid
            else:hi=mid
        lam=hi;steps=96
    right=q@(qtk/(eigen+lam)[:,None]);delta=(r@right.T).to(w.dtype)
    relative=float(delta.double().norm())/weight_norm
    if not bool(torch.isfinite(delta).all()) or relative>relative_cap:raise RuntimeError('stored edit violates fixed primary norm cap')
    predicted=r@(right.T@k);error=predicted-r
    dual=right.T@s+lam*right.T-k.T
    kkt=r@dual
    denominator=max(float((r@k.T).norm()),1e-300)
    gram=r.T@r
    preservation=float((gram*(right.T@c@right).T).sum())
    return dict(left=r,right=right,delta=delta,stats=dict(relative_cap=relative_cap,relative_norm=relative,
        original_weight_norm=weight_norm,target_delta_norm=target,unconstrained_delta_norm=unconstrained,
        multiplier=lam,bisection_steps=steps,normal_eigen_min=float(eigen[0]),normal_eigen_max=float(eigen[-1]),
        kkt_relative_residual=float(kkt.norm())/denominator,
        target_residual_norm=float(error.norm()),target_norm=float(r.norm()),
        relative_target_residuals=(error.norm(dim=0)/r.norm(dim=0).clamp_min(1e-300)).tolist(),
        covariance_energy=preservation,objective=.5*float(error.square().sum())+.5*preservation,
        factor_columns=keys.shape[1],base_optimizer_updates=0,value_optimizer_updates=0))


def factor_spectrum(left,right):
    if left.ndim!=2 or right.ndim!=2 or left.shape[1]!=right.shape[1]:raise ValueError('matching factor columns required')
    ql,rl=torch.linalg.qr(left.cpu().double(),mode='reduced')
    qr,rr=torch.linalg.qr(right.cpu().double(),mode='reduced')
    singular=torch.linalg.svdvals(rl@rr.T)
    return singular


def random_spectral_packet(reference,*,seed):
    if type(seed)is not int:raise ValueError('fixed explicit control seed required')
    left,right=reference['left'],reference['right'];singular=factor_spectrum(left,right)
    nominal=float(singular.norm());observed=float(reference['delta'].double().norm())
    if nominal<=0 or observed<=0:raise ValueError('positive reference norm required for matched random control')
    singular=singular*(observed/nominal);rank=len(singular)
    generator=torch.Generator(device='cpu').manual_seed(seed)
    a=torch.linalg.qr(torch.randn(left.shape[0],rank,dtype=torch.float64,generator=generator),mode='reduced')[0]
    b=torch.linalg.qr(torch.randn(right.shape[0],rank,dtype=torch.float64,generator=generator),mode='reduced')[0]
    a=a*singular[None,:];delta=(a@b.T).to(reference['delta'].dtype)
    return dict(left=a,right=b,delta=delta,seed=seed,intended_singular_values=singular.tolist(),
        intended_spectrum_scale=observed/nominal,
        relative_norm_match_error=abs(float(delta.double().norm())-observed)/observed)


def choose_common_layer(candidates,*,families,layers=(2,5,8,11)):
    expected={(f,layer) for f in families for layer in layers}
    observed={(r['fact'],r['layer']) for r in candidates}
    if len(candidates)!=len(expected) or observed!=expected or not families:
        raise ValueError('complete unique fact by layer candidates required')
    scores=[]
    for layer in layers:
        records=[r for r in candidates if r['layer']==layer]
        exact=sum(r['oracle_fit']['exact'] for r in records);items=sum(r['oracle_fit']['items'] for r in records)
        nll=sum(r['optimization']['trace'][-1]['nll'] for r in records)
        if items!=2*len(families) or not 0<=exact<=items or not math.isfinite(nll):raise ValueError('frozen two-fit metrics required')
        scores.append(dict(layer=layer,fit_exact=exact,fit_items=items,fit_nll_sum=nll))
    selected=min(scores,key=lambda r:(-r['fit_exact'],r['fit_nll_sum'],r['layer']))
    return selected['layer'],scores
