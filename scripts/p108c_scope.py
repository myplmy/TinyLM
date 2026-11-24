"""Feature-only edit-scope baselines; no language model, I/O, or answer lookup.

Labels and group IDs are fitting/selection metadata only. Runtime scoring takes
one numeric feature matrix and a frozen model. This is not a truth detector.
"""
from __future__ import annotations

import math
import numpy as np


def matrix(value, *, width=None):
    result = np.asarray(value, dtype=np.float64)
    if (result.ndim != 2 or min(result.shape) < 1 or
            (width is not None and result.shape[1] != width) or
            not np.isfinite(result).all()):
        raise ValueError("nonempty finite feature matrix of the declared width required")
    return result


def labels(value, count):
    result = np.asarray(value)
    if result.shape != (count,) or not np.isin(result, [0, 1]).all():
        raise ValueError("one binary label per fitting/selection feature required")
    return result.astype(bool)


def unit(value):
    value = matrix(value)
    scale = np.abs(value).max(axis=1, keepdims=True)
    if np.any(scale == 0):
        raise ValueError("zero direction cannot identify edit scope")
    result = value / scale
    return result / np.linalg.norm(result, axis=1, keepdims=True)


def group_weights(y, groups):
    y = labels(y, len(y))
    if len(groups) != len(y) or len(set(y.tolist())) != 2:
        raise ValueError("two classes and one explicit group per fitting row required")
    if any(not isinstance(g, str) or not g for g in groups):
        raise ValueError("nonempty fitting group IDs required")
    weights = np.empty(len(y), dtype=np.float64)
    for positive in (False, True):
        selected = np.flatnonzero(y == positive)
        unique = sorted({groups[i] for i in selected})
        for group in unique:
            indices = [i for i in selected if groups[i] == group]
            weights[indices] = .5 / len(unique) / len(indices)
    if not math.isclose(float(weights.sum()), 1., rel_tol=1e-12):
        raise RuntimeError("fitting class/group mass differs")
    return weights


def transformed(model, x):
    center, scale = (np.asarray(model[k], dtype=np.float64) for k in ("center", "scale"))
    if (center.ndim != 1 or scale.shape != center.shape or
            not np.isfinite(center).all() or not np.isfinite(scale).all() or np.any(scale <= 0)):
        raise ValueError("finite declared center and positive diagonal scale required")
    x = matrix(x, width=len(center))
    return unit((x - model["center"]) / model["scale"])


def fit_models(x, y, groups, delta, *, ridge_values=(1e-4, 1e-2, 1.)):
    x = matrix(x)
    y = labels(y, len(x))
    delta = matrix(delta, width=x.shape[1])
    weights = group_weights(y, groups)
    negative_weights = weights[~y] / weights[~y].sum()
    center = (x[~y] * negative_weights[:, None]).sum(axis=0)
    variance = ((x[~y] - center)**2 * negative_weights[:, None]).sum(axis=0)
    floor = max(float(np.sqrt(variance.mean())) * 1e-6, 1e-12)
    scale = np.maximum(np.sqrt(variance), floor)
    variants = [
        dict(name="DELTA_RESPONSE", kind="delta_response", delta=delta),
        dict(name="NEAREST_RAW", kind="nearest", center=np.zeros(x.shape[1]),
             scale=np.ones(x.shape[1])),
        dict(name="NEAREST_DIAGONAL_STANDARDIZED", kind="nearest", center=center, scale=scale),
    ]
    for record in variants[1:]:
        z = transformed(record, x)
        record.update(positive=z[y].copy(), negative=z[~y].copy())
    z = transformed(variants[2], x)
    root = np.sqrt(weights * len(weights))
    gram = (z @ z.T) * root[:, None] * root[None, :]
    target = np.where(y, 1., -1.)
    for regularizer in ridge_values:
        if (type(regularizer) not in (float, int) or
                not math.isfinite(regularizer) or regularizer <= 0):
            raise ValueError("positive finite declared ridge coefficient required")
        dual = np.linalg.solve(gram + regularizer * np.eye(len(x)), root * target)
        coefficient = z.T @ (root * dual)
        variants.append(dict(name="RIDGE_" + str(regularizer), kind="ridge",
                             center=center.copy(), scale=scale.copy(),
                             coefficient=coefficient, regularizer=regularizer))
    if len({v["name"] for v in variants}) != len(variants):
        raise ValueError("fitting candidates must have unique declared names")
    return variants, dict(class_group_weights=weights.tolist(),
                         negative_center_source="TRAIN_NEGATIVE_GROUP_BALANCED",
                         scale_floor=floor, fitting_rows=len(x),
                         positive_rows=int(y.sum()), negative_rows=int((~y).sum()))


def score(model, x):
    x = matrix(x)
    if model["kind"] == "off":
        return np.zeros(len(x), dtype=np.float64)
    if model["kind"] == "delta_response":
        delta = matrix(model["delta"], width=x.shape[1])
        # The numerator is the declared requested-delta response proxy.
        denominator = np.linalg.norm(x, axis=1)
        if np.any(denominator == 0):
            raise ValueError("nonzero feature for normalized response required")
        result = np.linalg.norm(x @ delta.T, axis=1) / denominator
    elif model["kind"] == "nearest":
        z = transformed(model, x)
        result = (z @ model["positive"].T).max(axis=1) - (z @ model["negative"].T).max(axis=1)
    elif model["kind"] == "ridge":
        result = transformed(model, x) @ model["coefficient"]
    else:
        raise ValueError("unknown frozen edit-scope model")
    if result.shape != (len(x),) or not np.isfinite(result).all():
        raise RuntimeError("nonfinite or malformed feature-only scope score")
    return result


def thresholds(train_scores):
    values = np.asarray(train_scores, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("finite one-dimensional TRAIN scores required")
    unique = np.unique(values)
    low = np.nextafter(unique[0], -np.inf)
    high = np.nextafter(unique[-1], np.inf)
    midpoints = unique[:-1]/2 + unique[1:]/2
    result = np.unique(np.concatenate(([low], midpoints, [high])))
    if not np.isfinite(result).all():
        raise ValueError("finite representable scope thresholds required")
    return result


def confusion(predicted, truth):
    predicted = np.asarray(predicted)
    if predicted.ndim != 1 or predicted.dtype != bool:
        raise ValueError("one boolean gate decision per input required")
    y = labels(truth, len(predicted))
    return dict(tp=int((predicted & y).sum()), fn=int((~predicted & y).sum()),
                fp=int((predicted & ~y).sum()), tn=int((~predicted & ~y).sum()))


def route(model, x, threshold):
    if type(threshold) not in (float, int) or not math.isfinite(threshold):
        raise ValueError("finite frozen routing threshold required")
    return score(model, x) >= threshold


def select(models, train_x, train_y, dev_x, dev_y, guard_x):
    train_x, dev_x, guard_x = matrix(train_x), matrix(dev_x), matrix(guard_x)
    train_y, dev_y = labels(train_y, len(train_x)), labels(dev_y, len(dev_x))
    records = []
    off = dict(name="ALWAYS_OFF", kind="off")
    records.append(dict(name=off["name"], threshold=1.,
                        train=confusion(route(off, train_x, 1.), train_y),
                        dev=confusion(route(off, dev_x, 1.), dev_y),
                        guard_false_positives=0, parameter_bytes=0))
    by_name = {off["name"]: off}
    for model in models:
        if model["name"] in by_name:
            raise ValueError("duplicate scope candidate name")
        by_name[model["name"]] = model
        training, validation, guard = [score(model, x) for x in (train_x, dev_x, guard_x)]
        parameter_bytes = sum(v.nbytes for v in model.values() if isinstance(v, np.ndarray))
        for threshold in thresholds(training):
            records.append(dict(name=model["name"], threshold=float(threshold),
                train=confusion(training >= threshold, train_y),
                dev=confusion(validation >= threshold, dev_y),
                guard_false_positives=int((guard >= threshold).sum()),
                parameter_bytes=parameter_bytes))
    eligible = [r for r in records if not(r["train"]["fp"] or r["dev"]["fp"] or r["guard_false_positives"])]
    # OFF is first when no candidate recovers a DEV positive.
    chosen = min(eligible, key=lambda r: (-r["dev"]["tp"], r["parameter_bytes"],
                                        -r["train"]["tp"], r["name"], r["threshold"]))
    return by_name[chosen["name"]], dict(selected=chosen, candidates=records,
        selection_rule="TRAIN_DEV_GUARD_FP0_DEV_TP_THEN_BYTES_TRAIN_TP_NAME_THRESHOLD",
        official_or_final_used=False)
