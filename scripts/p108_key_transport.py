"""Finite response geometry and explicitly bounded counterfactual labels."""
import torch


def response_geometry(response, target):
    if (response.ndim != 1 or response.shape != target.shape or not response.numel()
            or not torch.isfinite(response).all() or not torch.isfinite(target).all()):
        raise ValueError('matching finite response/target vectors required')
    a, b = response.detach().cpu().double(), target.detach().cpu().double()
    bn, an = float(b.norm()), float(a.norm())
    if not bn:
        raise ValueError('nonzero target required')
    return dict(norm_ratio=an / bn, projection_gain=float(a @ b) / bn**2,
                cosine=None if not an else float(a @ b) / (an * bn),
                relative_residual=float((a - b).norm()) / bn)


def evidence_flags(original, fixed, subject, full):
    if any(type(x) is not bool for x in (original, fixed, subject, full)):
        raise ValueError('explicit correctness booleans required')
    return dict(original_correct=original,
                fixed_value_insufficient=not fixed,
                key_response_loss=fixed and not subject,
                non_subject_loss=subject and not full,
                full_edit_rescue=not original and full,
                scope='COUNTERFACTUAL_INVOLVEMENT_NOT_UNIQUE_OR_POPULATION_CAUSE')
