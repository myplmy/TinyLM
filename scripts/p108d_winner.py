"""Minimum Frobenius edits for a certified affine, fixed-prefix vocabulary head.

This is a numerical half-space solver, not an answer verifier. All native
structure, materialization, generation and held-out quality gates live outside.
"""
from __future__ import annotations

import math
import time
import numpy as np


def finite_matrix(value, name):
    value = np.asarray(value, dtype=np.float64)
    if value.ndim != 2 or not value.size or not np.isfinite(value).all():
        raise ValueError(name + " must be a finite nonempty matrix")
    return value


def projected_keys(keys, protected, *, rank_rtol=1e-8):
    keys = finite_matrix(keys, "keys")
    protected = finite_matrix(protected, "protected keys")
    if keys.shape[1] != protected.shape[1] or not 0 < rank_rtol < 1:
        raise ValueError("same feature coordinates and valid rank tolerance required")
    _, singular, right = np.linalg.svd(protected, full_matrices=False)
    rank = int(np.sum(singular > rank_rtol * singular[0])) if singular[0] else 0
    basis = right[:rank]
    projected = keys - (keys @ basis.T) @ basis
    return projected, dict(rank=rank, feature_dimension=keys.shape[1],
                           relative_key_retention=float(np.linalg.norm(projected)) /
                           max(float(np.linalg.norm(keys)), 1e-30))


def winner_margins(scores, gold):
    scores = finite_matrix(scores, "scores")
    gold = np.asarray(gold)
    if (gold.shape != (len(scores),) or gold.dtype.kind not in "iu" or
            np.any(gold < 0) or np.any(gold >= scores.shape[1]) or scores.shape[1] < 2):
        raise ValueError("one valid integer gold class per score row required")
    competitors = scores.copy()
    competitors[np.arange(len(scores)), gold] = -np.inf
    rivals = competitors.argmax(axis=1)
    margins = scores[np.arange(len(scores)), gold] - competitors[np.arange(len(scores)), rivals]
    return margins, rivals


def plane_gram(left, right):
    left, right = finite_matrix(left, "left planes"), finite_matrix(right, "right planes")
    if len(left) != len(right):
        raise ValueError("one pair of rank-one factors per constraint required")
    return (left @ left.T) * (right @ right.T)


def solve_dual(gram, bounds, *, initial=None, max_iter=5000):
    """Solve the nonnegative dual; expose KKT and gap rather than only success."""
    from scipy.optimize import minimize
    gram = finite_matrix(gram, "constraint Gram")
    bounds = np.asarray(bounds, dtype=np.float64)
    if (gram.shape != (len(bounds), len(bounds)) or not np.isfinite(bounds).all()
            or not np.allclose(gram, gram.T, atol=1e-12, rtol=1e-12)):
        raise ValueError("symmetric Gram and one finite bound per plane required")
    start = np.zeros(len(bounds)) if initial is None else np.asarray(initial, dtype=np.float64)
    if start.shape != bounds.shape or not np.isfinite(start).all() or np.any(start < 0):
        raise ValueError("finite nonnegative warm start required")

    def objective(dual):
        product = gram @ dual
        return .5 * float(dual @ product) - float(bounds @ dual), product - bounds

    result = minimize(objective, start, method="L-BFGS-B", jac=True,
                      bounds=[(0., None)] * len(bounds),
                      options=dict(maxiter=max_iter, ftol=1e-15, gtol=1e-10,
                                   maxls=50, maxcor=40))
    dual = np.asarray(result.x)
    if not np.isfinite(dual).all():
        raise ValueError("solver produced non-finite dual")
    gradient = gram @ dual - bounds
    projected = np.where((dual <= 1e-12) & (gradient > 0), 0., gradient)
    norm2 = float(dual @ (gram @ dual))
    dual_value = float(bounds @ dual) - .5 * norm2
    primal_value = .5 * norm2
    gap = primal_value - dual_value
    return dual, dict(solver_success=bool(result.success), solver_message=str(result.message),
                      iterations=int(result.nit), function_evaluations=int(result.nfev),
                      projected_kkt_max=float(np.max(np.abs(projected))),
                      active_primal_violation=float(np.maximum(-gradient, 0.).max()),
                      primal_objective=primal_value, dual_objective=dual_value,
                      signed_gap=gap, relative_gap=abs(gap) / max(1., primal_value),
                      max_dual=float(dual.max()))


def solve_winners(head, residuals, keys, gold, gate, margins, *, protected=None,
                  rounds=32, max_iter=5000, tolerance=1e-5, check=None):
    head, residuals, keys = (finite_matrix(head, "head"),
                             finite_matrix(residuals, "residuals"),
                             finite_matrix(keys, "keys"))
    gold = np.asarray(gold, dtype=np.int64)
    margins = np.asarray(margins, dtype=np.float64)
    if (head.shape[1] != residuals.shape[1] or len(residuals) != len(keys) or
            margins.shape != (len(keys),) or not np.isfinite(margins).all() or
            np.any(margins <= 0) or not math.isfinite(gate) or gate == 0):
        raise ValueError("aligned nonempty targets, positive margins and nonzero finite gate required")
    baseline_scores = residuals @ head.T
    winner_margins(baseline_scores, gold)
    projected, protection = (keys.copy(), dict(rank=0, feature_dimension=keys.shape[1],
                                             relative_key_retention=1.))
    if protected is not None:
        projected, protection = projected_keys(keys, protected)
    delta = np.zeros((head.shape[1], keys.shape[1]), dtype=np.float64)
    constraints, constraint_set, dual, history = [], set(), np.zeros(0), []
    started = time.monotonic()
    left = right = normalized_bounds = None
    status = "CUTTING_PLANE_LIMIT"
    for iteration in range(rounds + 1):
        if check is not None:
            check()
        scores = (residuals + gate * (keys @ delta.T)) @ head.T
        actual_margins, rivals = winner_margins(scores, gold)
        violation = margins - actual_margins
        maximum = float(violation.max())
        if maximum <= tolerance:
            last = history[-1]["dual"] if history else dict(relative_gap=0., projected_kkt_max=0.)
            status = ("MINIMUM_NORM_NUMERICALLY_CERTIFIED" if last["relative_gap"] <= 1e-5
                      and last["projected_kkt_max"] <= 1e-5
                      else "FEASIBLE_WITHOUT_MINIMUM_NORM_CERT")
            break
        if iteration == rounds:
            break
        added = 0
        for position in np.where(violation > tolerance)[0]:
            constraint = (int(position), int(rivals[position]))
            if constraint not in constraint_set:
                constraints.append(constraint)
                constraint_set.add(constraint)
                added += 1
        if not added:
            status = "DUAL_CONVERGENCE_NOT_ESTABLISHED"
            break
        positions = np.array([item[0] for item in constraints])
        competitors = np.array([item[1] for item in constraints])
        differences = head[gold[positions]] - head[competitors]
        selected_keys = projected[positions]
        left_norms = np.linalg.norm(differences, axis=1)
        right_norms = np.linalg.norm(selected_keys, axis=1)
        raw_bounds = margins[positions] - np.einsum("ij,ij->i", differences, residuals[positions])
        scales = abs(gate) * left_norms * right_norms
        if np.any((scales <= 1e-20) & (raw_bounds > tolerance)):
            status = "NO_CONTROLLABLE_DIRECTION_FOR_REQUIRED_CONSTRAINT"
            break
        if np.any(scales <= 1e-20):
            status = "DEGENERATE_REDUNDANT_PLANE_REQUIRES_SEPARATE_REDUCTION"
            break
        left = np.sign(gate) * differences / left_norms[:, None]
        right = selected_keys / right_norms[:, None]
        normalized_bounds = raw_bounds / scales
        initial = np.pad(dual, (0, len(constraints) - len(dual)))
        dual, diagnostic = solve_dual(plane_gram(left, right), normalized_bounds,
                                      initial=initial, max_iter=max_iter)
        delta = left.T @ (dual[:, None] * right)
        history.append(dict(round=iteration + 1, constraints=len(constraints), added=added,
                            previous_maximum_raw_violation=maximum,
                            norm=float(np.linalg.norm(delta)), dual=diagnostic))
        if diagnostic["max_dual"] > 1e12:
            status = "DUAL_DIVERGENCE_NOT_A_PROOF_OF_INFEASIBILITY"
            break
    scores = (residuals + gate * (keys @ delta.T)) @ head.T
    actual_margins, rivals = winner_margins(scores, gold)
    report = dict(status=status, target_positions=len(keys), vocabulary=len(head),
                  constraint_count=len(constraints), constraints=constraints, history=history,
                  maximum_raw_violation=float((margins - actual_margins).max()),
                  correct_argmax=int(np.sum(scores.argmax(axis=1) == gold)),
                  minimum_actual_margin=float(actual_margins.min()),
                  norm=float(np.linalg.norm(delta)), protection=protection,
                  protected_response_norm=(None if protected is None else
                      float(np.linalg.norm(delta @ np.asarray(protected).T))),
                  wall_seconds=time.monotonic() - started)
    return delta, report


def materialize(before, requested, *, budget):
    before = np.asarray(before)
    requested = finite_matrix(requested, "requested delta")
    if before.dtype != np.float32 or before.shape != requested.shape or not np.isfinite(before).all():
        raise ValueError("native FP32 before matrix required")
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("positive finite physical budget required")
    after = before + requested.astype(np.float32)
    actual = after.astype(np.float64) - before.astype(np.float64)
    norm = float(np.linalg.norm(actual))
    return after, actual, dict(actual_norm=norm, requested_norm=float(np.linalg.norm(requested)),
        maximum_materialization_error=float(np.max(np.abs(actual - requested))),
        changed=int(np.sum(after != before)), total=int(before.size),
        changed_outside_requested=int(np.sum((after != before) & (requested == 0))),
        budget=budget, comparison="WITHIN_COMMON_BUDGET_NOT_EQUAL_NET" if norm <= budget * (1 + 2e-5)
        else "EXCEEDS_COMMON_BUDGET_SEPARATE_ARM")
