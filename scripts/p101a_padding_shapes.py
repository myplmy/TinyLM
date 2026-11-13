"""Exact execution-slot accounting without changing ordered optimizer groups."""
from collections import Counter

POLICIES = (32, 64, 128)


def width(lengths, quantum):
    if (quantum not in POLICIES or not lengths or any(type(x) is not int or not 1 <= x <= 1024 for x in lengths)):
        raise ValueError('real positive lengths <=1024 and registered quantum required')
    return quantum * ((max(lengths) + quantum - 1) // quantum)


def histogram_summary(histogram, *, batch=8):
    if batch != 8 or not histogram or any(type(w) is not int or not 1 <= w <= 1024 or type(n) is not int or n < 1 for w,n in histogram.items()):
        raise ValueError('positive width histogram and original micro8 required')
    count = sum(histogram.values())
    slots = batch * sum(w*n for w,n in histogram.items())
    squares = batch * sum(w*w*n for w,n in histogram.items())
    return dict(micros=count, slots=slots, pair_slots=squares,
                linear_ratio=slots/(batch*count*1024), pair_ratio=squares/(batch*count*1024**2),
                max_width=max(histogram), full1024_micros=histogram.get(1024,0),
                histogram={str(w):histogram[w] for w in sorted(histogram)})


def coverage(group):
    return {(int(q), w) for q, widths in group['widths'].items() for w in widths}


def select_groups(groups):
    if not groups: raise ValueError('nonempty complete groups required')
    if any(len(ws) != 16 for g in groups for ws in g['widths'].values()):
        raise ValueError('full16-micro optimizer group required')
    required = set().union(*(coverage(g) for g in groups))
    selected = []
    # Explicit safety boundaries first; preserve source order inside each group.
    forced = [max(range(len(groups)), key=lambda i: groups[i]['max_record']),
              max(range(len(groups)), key=lambda i: groups[i]['denominators']['1']/groups[i]['actual_x_tokens']),
              max(range(len(groups)), key=lambda i: sum(a!=b for a,b in zip(groups[i]['widths']['32'],groups[i]['widths']['64'])))]
    for i in forced:
        if i not in selected: selected.append(i)
    covered = set().union(*(coverage(groups[i]) for i in selected))
    while required-covered:
        remaining = [i for i in range(len(groups)) if i not in selected]
        i = max(remaining, key=lambda j:(len(coverage(groups[j])-covered), -j))
        if not coverage(groups[i])-covered: raise RuntimeError('width coverage stalled')
        selected.append(i); covered |= coverage(groups[i])
    return dict(indices=selected, covered=[list(x) for x in sorted(covered)],
                required=[list(x) for x in sorted(required)],
                algorithm='GREEDY_AFTER_LONGEST_DENSEST_ROUNDING_BOUNDARIES_NOT_GLOBAL_MINIMUM')
