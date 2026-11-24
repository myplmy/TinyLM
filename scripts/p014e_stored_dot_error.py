"""Independent NumPy byte unpack and high-precision scalar dot; no Torch I/O."""
from decimal import Decimal, Inexact, Rounded, localcontext
import numpy as np

def unpack_fp32(codes, scales, *, group, width):
    if (codes.dtype != np.uint8 or scales.dtype != np.float32 or codes.ndim != 3
            or scales.ndim != 2 or not isinstance(group, int) or group <= 0
            or not isinstance(width, int) or width % group or not bool(np.isfinite(scales).all())):
        raise ValueError('explicit finite FP32 scales/uint8 grouped payload required')
    rows = codes.shape[0]
    groups = width // group
    if (codes.shape != (rows, groups, (group + 4) // 5)
            or scales.shape != (rows, groups) or bool((codes > 242).any())):
        raise ValueError('complete grouped five-trit shape/code domain required')
    powers = np.array([1, 3, 9, 27, 81], dtype=np.int16)
    digits = ((codes.astype(np.int16)[..., None] // powers) % 3 - 1)
    digits = digits.reshape(rows, groups, -1)[..., :group].astype(np.float32)
    return np.ascontiguousarray((digits * scales[..., None]).reshape(rows, width))

def decimal_dot_fp32(x, weight):
    if (x.dtype != np.float32 or weight.dtype != np.float32 or x.ndim != 1
            or x.shape != weight.shape or not len(x)
            or not bool(np.isfinite(x).all() and np.isfinite(weight).all())):
        raise ValueError('same nonempty finite FP32 scalar-dot vectors required')
    with localcontext() as context:
        context.prec = 512
        context.clear_flags()
        value = Decimal(0)
        for left, right in zip(x, weight):
            value += Decimal.from_float(float(left)) * Decimal.from_float(float(right))
        if context.flags[Inexact]:
            raise ArithmeticError('independent Decimal operation rounded inexactly')
        return value, dict(precision=512, Inexact=False, Rounded=bool(context.flags[Rounded]))

def decimal_error(value, exact):
    with localcontext() as context:
        context.prec = 512
        context.clear_flags()
        result = abs(Decimal.from_float(float(value)) - exact)
        if context.flags[Inexact]:
            raise ArithmeticError('Decimal absolute-error calculation inexact')
        return result
