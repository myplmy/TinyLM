"""Canonical-answer content/EOT and competitor-margin metrics, not truth scores."""
import torch
import torch.nn.functional as F


def summarize(logits, targets, *, reference_competitor=None, terminal=4):
    if logits.ndim != 2 or targets.ndim != 1 or logits.shape[0] != len(targets):
        raise ValueError("one complete aligned target window required")
    if len(targets) < 2 or logits.shape[1] < 2 or not torch.isfinite(logits).all():
        raise ValueError("finite content plus terminal logits required")
    if int(targets[-1]) != terminal or int(targets.min()) < 0 or int(targets.max()) >= logits.shape[1]:
        raise ValueError("explicit final target ID and full vocabulary required")
    values = logits.detach().cpu().double()
    labels = targets.detach().cpu().long()
    losses = F.cross_entropy(values, labels, reduction="none")
    first = values[0]
    gold = int(labels[0])
    other = first.clone()
    other[gold] = -torch.inf
    competitor = int(other.argmax())
    reference = competitor if reference_competitor is None else reference_competitor
    if type(reference) is not int or not 0 <= reference < len(first) or reference == gold:
        raise ValueError("one nongold reference competitor required")
    last_other = values[-1].clone()
    last_other[terminal] = -torch.inf
    log_mass = torch.logsumexp(first, 0)
    return dict(mean_ce=float(losses.mean()), content_ce=float(losses[:-1].mean()),
        eot_ce=float(losses[-1]), content_contribution=float(losses[:-1].sum()/len(labels)),
        eot_contribution=float(losses[-1]/len(labels)), target_count=len(labels),
        first_gold=gold, first_argmax=int(first.argmax()), first_competitor=competitor,
        reference_competitor=reference, reference_margin=float(first[gold]-first[reference]),
        true_margin=float(first[gold]-other.max()),
        first_gold_rank=int((first > first[gold]).sum())+1,
        first_gold_probability=float(torch.exp(first[gold]-log_mass)),
        first_eot_probability=float(torch.exp(first[terminal]-log_mass)),
        eot_margin=float(values[-1,terminal]-last_other.max()),
        teacher_forced_content_argmax_match=bool(torch.equal(values[:-1].argmax(-1),labels[:-1])),
        teacher_forced_eot_argmax_match=int(values[-1].argmax()) == terminal,
        top_first_ids=first.topk(min(10,len(first))).indices.tolist())


def directional_projection(gradient, actual_delta):
    if gradient.shape != actual_delta.shape or not torch.isfinite(gradient).all() or not torch.isfinite(actual_delta).all():
        raise ValueError("finite aligned gradient and actual physical delta required")
    return float((gradient.detach().cpu().double()*actual_delta.detach().cpu().double()).sum())
