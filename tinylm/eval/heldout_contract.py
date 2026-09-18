"""P096 Q1 합성 held-out schema와 proof solver.

보호 데이터 경로를 읽지 않는다. relation item이 정답 하나를 형식적으로 증명하고 모든
distractor가 같은 의미 그래프에서 증명되지 않는지만 검증한다.
"""
from __future__ import annotations

from collections import deque


REQUIRED = {
    "id", "relation", "relation_subtype", "family_id", "template_id", "facts",
    "query_subject", "candidates", "gold_index", "gold_proof", "distractor_error_type",
    "difficulty_target", "difficulty_knobs",
}
DIFFICULTIES = {"easy", "mid", "hard"}
ERROR_TYPES = {"inverse", "necessary_sufficient", "temporal_reversal", "causal_correlation",
               "near_miss", "unsupported"}


def _reachable(facts, subject, relation, transitive):
    edges = [(f["subject"], f["object"]) for f in facts if f["relation"] == relation]
    if not transitive:
        return {b for a, b in edges if a == subject}
    graph = {}
    for a, b in edges:
        graph.setdefault(a, []).append(b)
    seen, queue = set(), deque([subject])
    while queue:
        cur = queue.popleft()
        for nxt in graph.get(cur, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def validate_item(item):
    errors = []
    missing = sorted(REQUIRED - set(item))
    if missing:
        return ["missing fields: " + ", ".join(missing)]
    candidates = item["candidates"]
    if len(candidates) < 2 or len(candidates) != len(set(candidates)):
        errors.append("candidates는 중복 없는 2개 이상")
    gold_index = item["gold_index"]
    if not isinstance(gold_index, int) or not 0 <= gold_index < len(candidates):
        errors.append("gold_index 범위 오류")
        return errors
    if item["difficulty_target"] not in DIFFICULTIES:
        errors.append("difficulty_target enum 오류")
    knobs = item["difficulty_knobs"]
    if set(knobs) != {"hops", "explicitness", "competing_clues", "distractor_distance"}:
        errors.append("difficulty_knobs 필드 오류")
    proof = item["gold_proof"]
    if proof.get("rule") not in {"direct", "transitive"}:
        errors.append("gold_proof.rule 오류")
    transitive = proof.get("rule") == "transitive"
    reachable = _reachable(item["facts"], item["query_subject"], item["relation"], transitive)
    proven = [i for i, candidate in enumerate(candidates) if candidate in reachable]
    if proven != [gold_index]:
        errors.append(f"정답 유일성 실패: proven={proven}, gold={gold_index}")
    edge_ids = proof.get("edge_ids")
    fact_ids = {f.get("id") for f in item["facts"]}
    if not edge_ids or not set(edge_ids).issubset(fact_ids):
        errors.append("gold_proof edge_ids가 facts에 닫히지 않음")
    distractors = {str(i) for i in range(len(candidates)) if i != gold_index}
    labels = item["distractor_error_type"]
    if set(labels) != distractors:
        errors.append("distractor_error_type key가 비정답 후보와 불일치")
    if any(label not in ERROR_TYPES for label in labels.values()):
        errors.append("distractor_error_type enum 오류")
    return errors


def validate_panel(items):
    errors = []
    seen = set()
    for item in items:
        if item.get("id") in seen:
            errors.append(f"duplicate id: {item.get('id')}")
        seen.add(item.get("id"))
        errors.extend(f"{item.get('id', '<missing>')}: {e}" for e in validate_item(item))
    return errors
