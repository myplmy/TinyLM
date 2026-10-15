"""Right-padding only; no truncation, conversation packing or training-default changes."""
import math


def width(lengths,trim,alignment=128,ceiling=1024):
    if not lengths or any(type(n) is not int or not 1<=n<=ceiling for n in lengths):
        raise ValueError('complete positive record lengths within fixed ceiling required')
    if type(alignment) is not int or alignment<1 or ceiling%alignment:
        raise ValueError('positive alignment dividing ceiling required')
    return min(ceiling,math.ceil(max(lengths)/alignment)*alignment) if trim else ceiling


def close_fp32(loss_a,loss_b,relative_l2,cosine):
    if any(not math.isfinite(v) for v in (loss_a,loss_b,relative_l2,cosine)):
        return False
    return abs(loss_a-loss_b)<=1e-4 and relative_l2<=1e-4 and cosine>=.999999
