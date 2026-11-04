"""P108 fixed-support controls for the actual, post-quantization intervention."""
import math
import torch


def row_sign_control(actual_delta, seed):
    if (not isinstance(actual_delta, torch.Tensor) or actual_delta.ndim != 2
            or not actual_delta.is_floating_point() or not torch.isfinite(actual_delta).all()
            or type(seed) is not int):
        raise ValueError('finite actual delta and integer seed required')
    gen = torch.Generator(device='cpu').manual_seed(seed)
    signs = (torch.randint(0, 2, (actual_delta.shape[0],), generator=gen) * 2 - 1).to(actual_delta)
    # D @ delta, with D an orthogonal diagonal matrix: same singular values,
    # elementwise support, absolute coefficients, column norms and Frobenius.
    return actual_delta * signs[:, None]


def control_receipt(actual_delta, control):
    if actual_delta.shape != control.shape:
        raise ValueError('control shape differs')
    return dict(same_support=bool(torch.equal(actual_delta.ne(0), control.ne(0))),
                same_absolute_coefficients=bool(torch.equal(actual_delta.abs(), control.abs())),
                target_norm=float(actual_delta.norm()), control_norm=float(control.norm()),
                sign_changed_nonzero=int(((actual_delta != control) & actual_delta.ne(0)).sum()))
