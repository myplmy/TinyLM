"""Keep each four-choice question independent inside one training batch."""

import numpy as np
import torch


def relation_groups_for(info, batch_size):
    packed = info.get("relation_groups")
    if packed is None:
        return ((1, info["gold"]),) if info["gold"] >= 0 else ()
    groups = tuple((int(segment), int(gold)) for segment, gold in packed)
    if (info["gold"] != -1 or info["decimal"] or len(groups) < 2
            or tuple(segment for segment, _ in groups) != tuple(range(1, len(groups)+1))
            or any(not 0 <= gold < batch_size for _, gold in groups)):
        raise ValueError("each packed relation requires its own distinct segment and valid winner")
    return groups


def keep_relation_winners(kinds, segments, groups):
    if not groups:
        return
    rows = np.arange(len(kinds))
    if len(groups) == 1:
        kinds[rows != groups[0][1]] = 0
        return
    for segment, winner in groups:
        group = segments == segment
        if not (group & (kinds != 0)).any(axis=1).all():
            raise ValueError("the grouped score requires a complete answer in each choice")
        kinds[group & (rows[:, None] != winner)] = 0


def relation_scores(nll, valid, labels, segments, groups, end):
    content = valid & labels.ne(end)
    if len(groups) == 1:
        yield -(nll * content).sum(1) / content.sum(1), groups[0][1]
        return
    memberships = torch.as_tensor(segments, device=labels.device)
    for segment, winner in groups:
        selected = content & memberships.eq(segment)
        yield -(nll * selected).sum(1) / selected.sum(1), winner
