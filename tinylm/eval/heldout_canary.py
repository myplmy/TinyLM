"""P096 Q2 bounded-canary provenance and preservation contracts."""
from __future__ import annotations

from collections import Counter

from .heldout_contract import validate_item


PROVENANCE_FIELDS = {"source_id", "candidate_id", "generation_rule", "preserved"}


def validate_candidate_bundle(baseline, candidates, *, max_slots=450, max_per_slot=2):
    errors = []
    baseline_by_id = {item.get("id"): item for item in baseline}
    if len(baseline_by_id) != len(baseline):
        errors.append("baseline duplicate id")
    if len(baseline) > max_slots:
        errors.append(f"baseline slots {len(baseline)} > {max_slots}")
    counts = Counter()
    candidate_ids = set()
    for candidate in candidates:
        provenance = candidate.get("provenance") or {}
        missing = PROVENANCE_FIELDS - set(provenance)
        if missing:
            errors.append(f"candidate provenance missing={sorted(missing)}")
            continue
        source_id = provenance["source_id"]
        counts[source_id] += 1
        if source_id not in baseline_by_id:
            errors.append(f"unknown source_id={source_id}")
        candidate_id = provenance["candidate_id"]
        if candidate_id in candidate_ids:
            errors.append(f"duplicate candidate_id={candidate_id}")
        candidate_ids.add(candidate_id)
        if provenance["preserved"]:
            candidate_body = {key: value for key, value in candidate.items() if key != "provenance"}
            if candidate_body != baseline_by_id.get(source_id):
                errors.append(f"preserved candidate changed source={source_id}")
        else:
            errors.extend(
                f"{candidate_id}: {error}"
                for error in validate_item(candidate, require_taxonomy=True)
            )
    for source_id, count in counts.items():
        if count > max_per_slot:
            errors.append(f"source {source_id} candidates={count} > {max_per_slot}")
    if len(candidates) > max_slots * max_per_slot:
        errors.append("candidate hard cap exceeded")
    return errors
