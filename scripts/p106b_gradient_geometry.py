"""CPU gradient geometry for diagnostics; never selects a production loss coefficient."""
import math
import torch


def geometry(left,right):
    if not left or set(left)!=set(right):raise ValueError('same nonempty named gradient space required')
    a=b=dot=0.
    for name,x in left.items():
        y=right[name]
        if x.device.type!='cpu'or y.device.type!='cpu'or x.shape!=y.shape or not bool(torch.isfinite(x).all())or not bool(torch.isfinite(y).all()):
            raise ValueError('same finite CPU gradient shapes required')
        x=x.double();y=y.double();a+=float(x.square().sum());b+=float(y.square().sum());dot+=float((x*y).sum())
    na=math.sqrt(a);nb=math.sqrt(b)
    return dict(left_norm=na,right_norm=nb,dot=dot,cosine=dot/(na*nb)if na and nb else None,
        right_over_left=nb/na if na else None,alpha_for_equal_norm=na/nb if nb else None,
        alpha_for_tenth_norm=.1*na/nb if nb else None,production_coefficient_selected=False)
